from django.http import JsonResponse, FileResponse
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ApplicationSerializer
from .services.sjr import get_sjr_quartile
from .services.rq_queue import enqueue_job
from .services.cron_jobs import process_position_closed_emails, send_position_closed_emails_job
from .services.ai_tasks import (
    normalize_source_text,
    process_course_plan_ai_job,
    process_phd_ai_job,
    process_scientific_field_ai_job,
)
from .services.submission_progress import (
    submission_progress_key,
    set_submission_progress,
)
from .utils.calculate import calculate_points
from .utils.email_utils import (
    build_email_html,
    send_resend_email,
    send_template_email,
    send_template_email_async,
    send_template_batch_email,
)
from .utils.application_change_utils import build_application_snapshot, diff_application_snapshots
from .models import (
    Application,
    Publication,
    User,
    Position,
    ScientificField,
    ScientificFieldProfile,
    ScientificFieldEmbedding,
    Course,
    UserProfile,
    ProfilePublication,
    VaultDocument,
    ApplicationDocument,
    PhdDegree,
    PhdProfile,
    PhdEmbedding,
    CoursePlan,
)
from .utils.jwt_utils import generate_jwt, decode_jwt
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from django.core.files.base import File
import logging
import time
import json
from datetime import datetime, time as dt_time
from concurrent.futures import ThreadPoolExecutor
from django.utils import timezone
from zoneinfo import ZoneInfo
from app.constants.departments import get_school_of_department
import os
import mimetypes

MAX_VAULT_UPLOAD_BYTES = 5 * 1024 * 1024
PHD_PDF_MAX_BYTES = 30 * 1024 * 1024
ALLOWED_VAULT_EXTENSIONS = {".pdf", ".doc", ".docx", ".odt"}
PHD_ABSTRACT_MIN_WORDS = 200
PHD_ABSTRACT_MAX_WORDS = 1000
PHD_KEYWORDS_MIN = 3
PHD_KEYWORDS_MAX = 10

logger = logging.getLogger(__name__)

def is_position_active(position, now=None):
    if not position or not position.start_date or not position.end_date:
        return False
    tz = ZoneInfo("Europe/Athens")
    if now is None:
        now = timezone.now().astimezone(tz)
    start_time = position.start_time or dt_time(0, 0)
    end_time = position.end_time or dt_time(23, 59)
    start_dt = datetime.combine(position.start_date, start_time, tzinfo=tz)
    end_dt = datetime.combine(position.end_date, end_time, tzinfo=tz)
    return start_dt <= now <= end_dt


def validate_vault_file(uploaded_file, doc_type=None):
    if not uploaded_file:
        return "Missing file."
    max_bytes = PHD_PDF_MAX_BYTES if doc_type == "phd" else MAX_VAULT_UPLOAD_BYTES
    if uploaded_file.size and uploaded_file.size > max_bytes:
        max_mb = int(max_bytes / (1024 * 1024))
        return f"Το αρχείο πρέπει να είναι έως {max_mb}MB."
    filename = uploaded_file.name or ""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_VAULT_EXTENSIONS:
        return "Επιτρέπονται μόνο αρχεία PDF, DOC, DOCX, ODT."
    return None


def build_scientific_field_source_text(name, courses):
    lines = [f"Επιστημονικό Πεδίο: {normalize_source_text(name)}"]
    for idx, course in enumerate(courses or [], start=1):
        course_name = normalize_source_text(course.get("name"))
        description = normalize_source_text(course.get("description"))
        lines.extend(
            [
                "",
                f"Μάθημα {idx}: {course_name}",
                f"Περιγραφή Μαθήματος {idx}:",
                description,
            ]
        )
    return "\n".join(lines).strip()

SINGLE_DOC_TYPES = {
    "cv",
    "phd",
    "doatap",
    "course_plan",
    "military",
    "public_employee_permission",
    "not_participated_declaration",
    "eu_citizen_greek_language_certificate",
    "responsible_declaration",
}

MULTI_DOC_TYPES = {
    "bio_supporting",
    "employment_certificate",
    "other",
}

PROFILE_DOC_FIELD_MAP = {
    "cvDocument": "cv",
    "phdDocument": "phd",
    "doatapDocument": "doatap",
    "coursePlanDocument": "course_plan",
    "militaryObligationsDocument": "military",
    "publicEmployeePermissionDocument": "public_employee_permission",
    "notParticipatedDeclarationDocument": "not_participated_declaration",
    "euCitizenGreekLanguageCertificateDocument": "eu_citizen_greek_language_certificate",
    "responsibleDeclarationDocument": "responsible_declaration",
}

COURSE_PLAN_FIELDS_MAP = {
    "generalDescription": "general_description",
    "learningObjectives": "learning_objectives",
    "courseSchedule": "course_schedule",
    "deliveryMethods": "delivery_methods",
    "bibliographyMaterial": "bibliography_material",
    "learningOutcomes": "learning_outcomes",
    "assessmentMethodsCriteria": "assessment_methods_criteria",
}


def profile_doc_info(doc):
    if not doc:
        return {"id": None, "name": None, "downloadPath": None, "isDefault": False}
    is_used_in_application = ApplicationDocument.objects.filter(vault_document=doc).exists()
    is_used_in_degree = PhdDegree.objects.filter(
        models.Q(vault_document=doc) | models.Q(doatap_document=doc)
    ).exists()
    return {
        "id": doc.id,
        "name": os.path.basename(doc.file.name) if doc.file else None,
        "downloadPath": f"/api/profile/documents/{doc.id}",
        "isDefault": doc.is_default,
        "isUsed": is_used_in_application,
        "isUsedInApplication": is_used_in_application,
        "isUsedInPhdDegree": is_used_in_degree,
        "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


def get_default_profile_doc(user, doc_type):
    default_doc = (
        VaultDocument.objects.filter(
            user=user, doc_type=doc_type, is_default=True
        )
        .order_by("-uploaded_at", "-id")
        .first()
    )
    if default_doc:
        return default_doc
    return (
        VaultDocument.objects.filter(user=user, doc_type=doc_type)
        .order_by("-uploaded_at", "-id")
        .first()
    )


def ensure_single_default(user, doc_type, keep_id=None):
    queryset = VaultDocument.objects.filter(user=user, doc_type=doc_type)
    if keep_id:
        queryset = queryset.exclude(id=keep_id)
    queryset.update(is_default=False)


def build_vault_path(user_id, filename):
    return f"documents/user_{user_id}/vault/{filename}"


def build_application_path(user_id, application_id, filename):
    return f"documents/user_{user_id}/application_{application_id}/{filename}"


def move_vault_document_file(profile_doc, target_path):
    if not profile_doc or not profile_doc.file or not profile_doc.file.name:
        return
    if os.path.dirname(profile_doc.file.name) == os.path.dirname(target_path):
        return

    storage = profile_doc.file.storage
    old_name = profile_doc.file.name
    target_name = storage.get_available_name(target_path)
    with profile_doc.file.open("rb") as source_file:
        new_name = storage.save(target_name, File(source_file))
    profile_doc.file.name = new_name
    profile_doc.save(update_fields=["file"])
    if storage.exists(old_name):
        storage.delete(old_name)


def ensure_doc_in_application_folder(profile_doc, application_id):
    filename = os.path.basename(profile_doc.file.name or "document")
    target_path = build_application_path(profile_doc.user_id, application_id, filename)
    move_vault_document_file(profile_doc, target_path)


def cleanup_profile_doc_if_orphan(profile_doc):
    if not profile_doc:
        return
    if ApplicationDocument.objects.filter(vault_document=profile_doc).exists():
        return
    if PhdDegree.objects.filter(
        models.Q(vault_document=profile_doc) | models.Q(doatap_document=profile_doc)
    ).exists():
        return
    if profile_doc.file and profile_doc.file.name:
        filename = os.path.basename(profile_doc.file.name)
        target_path = build_vault_path(profile_doc.user_id, filename)
        move_vault_document_file(profile_doc, target_path)
    if not VaultDocument.objects.filter(
        user=profile_doc.user, doc_type=profile_doc.doc_type, is_default=True
    ).exists():
        profile_doc.is_default = True
        profile_doc.save(update_fields=["is_default"])


def build_application_document_maps(application):
    links = (
        ApplicationDocument.objects.filter(application=application)
        .select_related("vault_document")
        .order_by("-created_at", "-id")
    )
    if not links.exists():
        return None, None, False

    single_docs = {}
    multi_docs = {"bio_supporting": [], "employment_certificate": []}

    for link in links:
        doc = link.vault_document
        doc_info = {
            "id": doc.id,
            "name": os.path.basename(doc.file.name) if doc.file else None,
            "downloadPath": f"/api/applicant/{application.id}/documents/{doc.id}",
        }
        if link.doc_type in MULTI_DOC_TYPES:
            multi_docs[link.doc_type].append(doc_info)
        elif link.doc_type not in single_docs:
            single_docs[link.doc_type] = doc_info

    return single_docs, multi_docs, True


def build_application_form(app):
    single_docs, multi_docs, has_links = build_application_document_maps(app)

    def single_doc_name(doc_type):
        if has_links and doc_type in single_docs:
            return single_docs[doc_type]["name"]
        return None

    def single_doc_id(doc_type):
        if has_links and doc_type in single_docs:
            return single_docs[doc_type]["id"]
        return None

    def multi_doc_list(doc_type, fallback_queryset=None):
        if has_links:
            return multi_docs.get(doc_type, [])
        return []

    existing_course_plans = {
        str(course_plan.course_id): {
            "generalDescription": course_plan.general_description or "",
            "learningObjectives": course_plan.learning_objectives or "",
            "courseSchedule": course_plan.course_schedule or "",
            "deliveryMethods": course_plan.delivery_methods or "",
            "bibliographyMaterial": course_plan.bibliography_material or "",
            "learningOutcomes": course_plan.learning_outcomes or "",
            "assessmentMethodsCriteria": course_plan.assessment_methods_criteria or "",
        }
        for course_plan in CoursePlan.objects.filter(application=app)
    }

    return {
        "id": app.id,
        "positionId": app.position.id if app.position else None,
        "positionEndDate": app.position.end_date.strftime("%d-%m-%Y") if app.position and app.position.end_date else "",
        "positionEndTime": app.position.end_time.strftime("%H:%M") if app.position and app.position.end_time else "",
        "phoneNumber": app.phone_number,
        "landlineNumber": app.landline_number,
        "streetAddress": app.street_address,
        "city": app.city,
        "postalCode": app.postal_code,
        "isPublicEmployee": app.is_public_employee,
        "phdTitle": app.phd_title,
        "phdAcquisitionDate": app.phd_acquisition_date,
        "phdIsFromForeignInstitute": app.phd_is_from_foreign_institute,
        "phdDegreeId": app.phd_degree_id,
        "phdAbstract": app.phd_abstract or "",
        "phdKeywords": app.phd_keywords or [],
        "scientificField": app.position.scientific_field.name if app.position else None,
        "workExperience": app.work_experience,
        "hasNotParticipatedInPastProgram": app.has_not_participated_in_past_program,
        "isEuCitizenNonGreek": app.is_eu_citizen_non_greek,
        "cvDocument": single_doc_name("cv"),
        "cvDocumentId": single_doc_id("cv"),
        "bioSupportingDocuments": multi_doc_list("bio_supporting"),
        "phdDocument": single_doc_name("phd"),
        "phdDocumentId": single_doc_id("phd"),
        "doatapDocument": single_doc_name("doatap"),
        "doatapDocumentId": single_doc_id("doatap"),
        "coursePlanDocument": single_doc_name("course_plan"),
        "coursePlanDocumentId": single_doc_id("course_plan"),
        "militaryObligationsDocument": single_doc_name("military"),
        "militaryObligationsDocumentId": single_doc_id("military"),
        "employmentCertificates": multi_doc_list("employment_certificate"),
        "publicEmployeePermissionDocument": single_doc_name("public_employee_permission"),
        "publicEmployeePermissionDocumentId": single_doc_id(
            "public_employee_permission"
        ),
        "notParticipatedDeclarationDocument": single_doc_name("not_participated_declaration"),
        "notParticipatedDeclarationDocumentId": single_doc_id(
            "not_participated_declaration"
        ),
        "euCitizenGreekLanguageCertificateDocument": single_doc_name(
            "eu_citizen_greek_language_certificate"
        ),
        "euCitizenGreekLanguageCertificateDocumentId": single_doc_id(
            "eu_citizen_greek_language_certificate"
        ),
        "responsibleDeclarationDocument": single_doc_name("responsible_declaration"),
        "responsibleDeclarationDocumentId": single_doc_id("responsible_declaration"),
        "publications": [
            {
                "id": publication.id,
                "type": publication.type,
                "publicationTitle": publication.publication_title,
                "journalConfTitle": publication.journal_conf_title,
                "year": publication.year,
                "issn": publication.issn,
                "country": publication.country,
                "quartile": publication.quartile,
                "authors": publication.authors or "",
                "publisher": publication.publisher,
            }
            for publication in app.publications.all()
        ],
        "coursePlans": existing_course_plans,
        "positionEndDate": app.position.end_date if app.position else None,
        "positionStartDate": app.position.start_date if app.position else None,
    }

@csrf_exempt
@api_view(["POST"])
def user_register(request):
    data = request.data
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password")
    gender = data.get("gender")

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already registered."}, status=400)

    if gender not in {"male", "female"}:
        return JsonResponse({"error": "Gender is required."}, status=400)

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role="guest",
        gender=gender,
    )
    user.set_password(password)
    user.save()

    try:
        send_template_email_async("guest_registration", user.email)
    except Exception as exc:
        print(f"Registration email failed: {exc}")

    return JsonResponse({"message": "Registration successful."}, status=200)

# Register Admin
@csrf_exempt
@api_view(["POST"])
def user_register_admin(request):
    # Check for Bearer token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    # Decode token and get user
    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user or user.role != "admin":
        return JsonResponse({"error": "Only admins can register a new admin."}, status=403)

    # Get new admin data
    data = request.data
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password")

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already registered."}, status=400)

    new_admin = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role="admin"
    )
    new_admin.set_password(password)
    new_admin.save()

    try:
        send_template_email_async("admin_registration", new_admin.email)
    except Exception as exc:
        print(f"Admin registration email failed: {exc}")

    return JsonResponse({"message": "Admin registration successful."}, status=200)

# Login
@csrf_exempt
@api_view(["POST"])
def user_login(request):
    data = request.data
    email = data.get("email")
    password = data.get("password")
    try:
        user = User.objects.get(email=email)
        if user.check_password(password):
            token = generate_jwt(user.id)
            return JsonResponse({"token": token}, status=200)
        else:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)


@csrf_exempt
@api_view(["GET"])
def users_list(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    requester = User.objects.filter(id=user_id).first()
    if not requester or requester.role != "admin":
        return JsonResponse({"error": "Only admins can view users."}, status=403)

    role = (request.GET.get("role") or "").strip().lower()
    if role not in {"applicant", "guest", "admin"}:
        return JsonResponse({"error": "Invalid role."}, status=400)

    users = User.objects.filter(role=role).select_related("profile")
    data = []

    if role == "applicant":
        users = users.annotate(applications_count=Count("applications"))
        for user in users:
            profile = getattr(user, "profile", None)
            data.append({
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "gender": user.gender,
                "mobileNumber": profile.mobile_number if profile else None,
                "landlineNumber": profile.landline_number if profile else None,
                "applicationsCount": user.applications_count or 0,
            })
    elif role == "guest":
        for user in users:
            data.append({
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "gender": user.gender,
                "email": user.email,
                "rankingVisits": user.ranking_visits or 0,
            })
    else:
        for user in users:
            data.append({
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
            })

    return JsonResponse({"users": data}, status=200)


@csrf_exempt
@api_view(["POST"])
def increment_guest_ranking_visit(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)
    if user.role != "guest":
        return JsonResponse({"error": "Only guests can increment ranking visits."}, status=403)

    user.ranking_visits = (user.ranking_visits or 0) + 1
    user.save(update_fields=["ranking_visits"])
    return JsonResponse({"rankingVisits": user.ranking_visits}, status=200)


@csrf_exempt
@api_view(["POST"])
def email_test(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    data = request.data
    to_email = data.get("to") or user.email
    template_name = (data.get("template") or "").strip()
    subject = data.get("subject") or "ProfRanker test email"
    body_html = data.get("html") or "<p>This is a test email from ProfRanker.</p>"
    text = data.get("text") or "This is a test email from ProfRanker."

    if template_name:
        template_context = data.get("context")
        if isinstance(template_context, str):
            try:
                template_context = json.loads(template_context)
            except json.JSONDecodeError:
                template_context = {}
        if not isinstance(template_context, dict):
            template_context = {}
        try:
            result = send_template_email(template_name, to_email, template_context)
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"message": "Email sent.", "result": result}, status=200)

    headline = data.get("headline") or subject

    try:
        html = build_email_html(subject=subject, headline=headline, body_html=body_html)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        result = send_resend_email(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"message": "Email sent.", "result": result}, status=200)


@csrf_exempt
@api_view(["POST"])
def cron_send_position_closed_emails(request):
    secret = request.headers.get("X-CRON-SECRET", "")
    if not secret or secret != settings.CRON_SECRET:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        job = enqueue_job(send_position_closed_emails_job)
    except Exception as exc:
        print(f"RQ enqueue failed: {exc}")
        result = process_position_closed_emails()
        result["mode"] = "sync-fallback"
        return JsonResponse(result, status=200)

    return JsonResponse({"job_id": job.id, "status": "queued"}, status=202)

# Get User by Token
@api_view(["GET"])
def get_user_by_token(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    # Prepare user data in camelCase
    profile = UserProfile.objects.filter(user=user).first()

    user_data = {
        "id": user.id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "mobileNumber": profile.mobile_number if profile else None,
        "landlineNumber": profile.landline_number if profile else None,
        "streetAddress": profile.street_address if profile else None,
        "city": profile.city if profile else None,
        "postalCode": profile.postal_code if profile else None,
        "role": user.role,
        "gender": user.gender,
    }
    include = (request.query_params.get("include") or "").lower()
    include_apps = "applications" in include

    if not include_apps:
        return JsonResponse(user_data, safe=False)

    user_data["applications"] = []

    applications = list(
        user.applications.select_related("position", "position__scientific_field")
        .prefetch_related("publications")
        .order_by("-submitted_at", "-id")
    )
    if applications:
        forms = [build_application_form(app) for app in applications]
        user_data["applications"] = forms
        user_data["form"] = forms[0]

    return JsonResponse(user_data, safe=False)


def build_profile_response(user, profile, applications=None):
    tz = ZoneInfo("Europe/Athens")

    applications_data = []
    has_submitted_applications = False
    for application in applications or []:
        has_submitted_applications = True
        sf = application.position.scientific_field if application.position else None
        submit_date = (
            timezone.localtime(application.submitted_at, tz).strftime("%d-%m-%Y %H:%M")
            if application.submitted_at
            else ""
        )
        position_end_date = (
            application.position.end_date.strftime("%d-%m-%Y")
            if application.position and application.position.end_date
            else ""
        )
        position_start_date = (
            application.position.start_date.strftime("%d-%m-%Y")
            if application.position and application.position.start_date
            else ""
        )
        position_start_time = (
            application.position.start_time.strftime("%H:%M")
            if application.position and application.position.start_time
            else ""
        )
        position_end_time = (
            application.position.end_time.strftime("%H:%M")
            if application.position and application.position.end_time
            else ""
        )
        applications_data.append(
            {
                "id": application.id,
                "positionId": application.position.id if application.position else None,
                "scientificField": sf.name if sf else "",
                "department": sf.department if sf else "",
                "school": get_school_of_department(sf.department) if sf else "",
                "submitDate": submit_date,
                "positionStartDate": position_start_date,
                "positionStartTime": position_start_time,
                "positionEndDate": position_end_date,
                "positionEndTime": position_end_time,
                "isActive": is_position_active(application.position),
                "totalPoints": application.total_points,
            }
        )

    profile_publications = [
        serialize_profile_publication(publication)
        for publication in ProfilePublication.objects.filter(user=user)
        .order_by("-updated_at", "-id")
    ]

    document_vault = {}
    for doc in VaultDocument.objects.filter(user=user).order_by("-uploaded_at", "-id"):
        document_vault.setdefault(doc.doc_type, []).append(profile_doc_info(doc))

    phd_degrees = []
    for degree in (
        PhdDegree.objects.filter(user=user)
        .select_related("vault_document", "doatap_document")
        .order_by("-acquired_at", "-id")
    ):
        phd_degrees.append(
            {
                "id": degree.id,
                "title": degree.title,
                "acquiredAt": degree.acquired_at,
                "isForeignInstitute": bool(degree.is_foreign_institute),
                "abstract": degree.abstract or "",
                "keywords": degree.keywords or [],
                "document": profile_doc_info(degree.vault_document),
                "doatapDocument": profile_doc_info(degree.doatap_document)
                if degree.is_foreign_institute
                else None,
            }
        )

    return {
        "user": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "mobileNumber": profile.mobile_number,
            "landlineNumber": profile.landline_number,
            "streetAddress": profile.street_address,
            "city": profile.city,
            "postalCode": profile.postal_code,
            "role": user.role,
            "gender": user.gender,
        },
        "canEditIdentity": not has_submitted_applications,
        "applicationDefaults": {
            "isPublicEmployee": bool(profile.is_public_employee),
            "isEuCitizenNonGreek": bool(profile.is_eu_citizen_non_greek),
            "hasNotParticipatedInPastProgram": bool(profile.has_not_participated_in_past_program),
            "workExperience": profile.work_experience,
        },
        "documents": {
            "cv": profile_doc_info(get_default_profile_doc(user, "cv")),
            "phd": profile_doc_info(get_default_profile_doc(user, "phd")),
            "doatap": profile_doc_info(get_default_profile_doc(user, "doatap")),
            "coursePlan": profile_doc_info(get_default_profile_doc(user, "course_plan")),
            "military": profile_doc_info(get_default_profile_doc(user, "military")),
            "publicEmployeePermission": profile_doc_info(
                get_default_profile_doc(user, "public_employee_permission")
            ),
            "notParticipatedDeclaration": profile_doc_info(
                get_default_profile_doc(user, "not_participated_declaration")
            ),
            "euCitizenGreekLanguageCertificate": profile_doc_info(
                get_default_profile_doc(user, "eu_citizen_greek_language_certificate")
            ),
            "responsibleDeclaration": profile_doc_info(
                get_default_profile_doc(user, "responsible_declaration")
            ),
        },
        "phdDegrees": phd_degrees,
        "documentVault": document_vault,
        "applications": applications_data,
        "profilePublications": profile_publications,
    }


@api_view(["GET", "PUT"])
def profile_detail(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    applications = list(
        Application.objects.filter(user=user)
        .select_related("position", "position__scientific_field")
        .prefetch_related("publications")
        .order_by("-submitted_at", "-id")
    )

    if request.method == "PUT":
        data = request.data
        application_defaults = data.get("applicationDefaults")
        if isinstance(application_defaults, str):
            try:
                application_defaults = json.loads(application_defaults)
            except json.JSONDecodeError:
                application_defaults = {}
        if application_defaults is None:
            application_defaults = {}

        first_name = data.get("firstName")
        last_name = data.get("lastName")
        email = data.get("email")
        mobile_number = data.get("mobileNumber")
        landline_number = data.get("landlineNumber")
        street_address = data.get("streetAddress")
        city = data.get("city")
        postal_code = data.get("postalCode")
        gender = data.get("gender")
        has_gender = "gender" in data

        is_public_employee = application_defaults.get(
            "isPublicEmployee", data.get("isPublicEmployee")
        )
        is_eu_citizen_non_greek = application_defaults.get(
            "isEuCitizenNonGreek", data.get("isEuCitizenNonGreek")
        )
        has_not_participated_in_past_program = application_defaults.get(
            "hasNotParticipatedInPastProgram",
            data.get("hasNotParticipatedInPastProgram"),
        )
        work_experience = application_defaults.get(
            "workExperience", data.get("workExperience")
        )

        profile_publications = data.get("profilePublications")
        has_profile_publications = "profilePublications" in data
        if isinstance(profile_publications, str):
            try:
                profile_publications = json.loads(profile_publications)
            except json.JSONDecodeError:
                profile_publications = []


        def coerce_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
            return bool(value) if value is not None else None

        if email is not None and email != user.email:
            return JsonResponse(
                {
                    "error": "Δεν επιτρέπεται αλλαγή του email.",
                },
                status=400,
            )

        has_submitted_applications = Application.objects.filter(user=user).exists()

        if has_submitted_applications:
            attempted_identity_change = False
            if first_name is not None and first_name != user.first_name:
                attempted_identity_change = True
            if last_name is not None and last_name != user.last_name:
                attempted_identity_change = True
            if attempted_identity_change:
                return JsonResponse(
                    {
                        "error": "Δεν επιτρέπεται αλλαγή ονόματος μετά την πρώτη υποβολή αίτησης.",
                    },
                    status=400,
                )

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            user.email = email
        if mobile_number is not None:
            profile.mobile_number = mobile_number
        if landline_number is not None:
            profile.landline_number = landline_number
        if street_address is not None:
            profile.street_address = street_address
        if city is not None:
            profile.city = city
        if postal_code is not None:
            profile.postal_code = postal_code
        if has_gender and gender in {"male", "female", None, ""}:
            user.gender = gender or None
        user.save()

        if is_public_employee is not None:
            profile.is_public_employee = coerce_bool(is_public_employee)
        if is_eu_citizen_non_greek is not None:
            profile.is_eu_citizen_non_greek = coerce_bool(is_eu_citizen_non_greek)
        if has_not_participated_in_past_program is not None:
            profile.has_not_participated_in_past_program = coerce_bool(
                has_not_participated_in_past_program
            )
        if work_experience is not None:
            if work_experience == "":
                profile.work_experience = None
            else:
                try:
                    profile.work_experience = int(work_experience)
                except (TypeError, ValueError):
                    profile.work_experience = None

        if has_profile_publications:
            submitted_ids = set()
            existing_publications = {
                publication.id: publication
                for publication in ProfilePublication.objects.filter(user=user)
            }
            for item in profile_publications or []:
                payload = build_profile_publication_payload(item or {})
                publication_id = item.get("id") if isinstance(item, dict) else None
                if publication_id and publication_id in existing_publications:
                    db_publication = existing_publications[publication_id]
                    db_publication.type = payload["type"] or None
                    db_publication.publication_title = payload["publication_title"] or None
                    db_publication.journal_conf_title = payload["journal_conf_title"] or None
                    db_publication.year = payload["year"] or None
                    db_publication.issn = payload["issn"] or None
                    db_publication.country = payload["country"] or None
                    db_publication.quartile = payload["quartile"] or None
                    db_publication.authors = payload["authors"] or ""
                    db_publication.publisher = payload["publisher"] or None
                    db_publication.save()
                    submitted_ids.add(db_publication.id)
                else:
                    new_publication = ProfilePublication.objects.create(
                        user=user,
                        type=payload["type"] or None,
                        publication_title=payload["publication_title"] or None,
                        journal_conf_title=payload["journal_conf_title"] or None,
                        year=payload["year"] or None,
                        issn=payload["issn"] or None,
                        country=payload["country"] or None,
                        quartile=payload["quartile"] or None,
                        authors=payload["authors"] or "",
                        publisher=payload["publisher"] or None,
                    )
                    submitted_ids.add(new_publication.id)

            for publication_id, db_publication in existing_publications.items():
                if publication_id not in submitted_ids:
                    db_publication.delete()

        profile.save()

        def parse_keywords(value):
            if value is None:
                return []
            if isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str):
                if value.strip() == "":
                    items = []
                else:
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            items = [str(item).strip() for item in parsed if str(item).strip()]
                        else:
                            items = [value.strip()]
                    except json.JSONDecodeError:
                        items = [value.strip()]
            else:
                items = [str(value).strip()] if str(value).strip() else []
            deduped = []
            seen = set()
            for item in items:
                key = item.lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(item)
            return deduped

        phd_degree_id = data.get("phdDegreeId")
        if phd_degree_id not in {None, "", "null", "None"}:
            try:
                degree = PhdDegree.objects.filter(id=int(phd_degree_id), user=user).first()
            except (TypeError, ValueError):
                degree = None
            if degree:
                if "phdTitle" in data:
                    degree.title = data.get("phdTitle") or ""
                if "phdAcquisitionDate" in data:
                    degree.acquired_at = data.get("phdAcquisitionDate") or degree.acquired_at
                if "phdIsFromForeignInstitute" in data:
                    degree.is_foreign_institute = coerce_bool(data.get("phdIsFromForeignInstitute"))
                if "phdAbstract" in data:
                    degree.abstract = data.get("phdAbstract") or ""
                if "phdKeywords" in data:
                    degree.keywords = parse_keywords(data.get("phdKeywords"))
                degree.save()

    response = build_profile_response(user, profile, applications)
    return JsonResponse(response, safe=False)


@api_view(["GET"])
def admin_profile_detail(request, user_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    requester_id = payload.get("user_id")
    requester = User.objects.filter(id=requester_id).first()
    if not requester or requester.role != "admin":
        return JsonResponse({"error": "Only admins can view profiles."}, status=403)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    applications = list(
        Application.objects.filter(user=user)
        .select_related("position", "position__scientific_field")
        .prefetch_related("publications")
        .order_by("-submitted_at", "-id")
    )

    return JsonResponse(build_profile_response(user, profile, applications), safe=False)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def profile_documents_upload(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    profile, _ = UserProfile.objects.get_or_create(user=user)

    for incoming, doc_type in PROFILE_DOC_FIELD_MAP.items():
        new_file = request.FILES.get(incoming)
        if new_file:
            profile_doc = VaultDocument.objects.create(
                user=user,
                doc_type=doc_type,
                file=new_file,
                is_default=True,
            )
            if doc_type in SINGLE_DOC_TYPES:
                ensure_single_default(user, doc_type, keep_id=profile_doc.id)
    applications = list(
        Application.objects.filter(user=user)
        .select_related("position", "position__scientific_field")
        .order_by("-submitted_at", "-id")
    )
    response = build_profile_response(user, profile, applications)
    return JsonResponse(response, safe=False)


@api_view(["GET"])
def profile_document_download(request, doc_key):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        return JsonResponse({"error": "Profile not found."}, status=404)

    doc_type_map = {
        "cv": "cv",
        "phd": "phd",
        "doatap": "doatap",
        "course_plan": "course_plan",
        "courseplan": "course_plan",
        "coursePlan": "course_plan",
        "military": "military",
    }

    file_field = None
    if str(doc_key).isdigit():
        if user.role == "admin":
            profile_doc = VaultDocument.objects.filter(id=int(doc_key)).first()
        else:
            profile_doc = VaultDocument.objects.filter(
                id=int(doc_key), user=user
            ).first()
        file_field = profile_doc.file if profile_doc else None
    else:
        mapped_type = doc_type_map.get(doc_key, doc_key)
        profile_doc = get_default_profile_doc(user, mapped_type)
        file_field = profile_doc.file if profile_doc else None

    if not file_field or not file_field.name:
        return JsonResponse({"error": "Document not found."}, status=404)

    filename = os.path.basename(file_field.name)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    response = FileResponse(
        file_field.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )
    return response


@api_view(["PUT", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
def profile_document_manage(request, doc_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    profile_doc = VaultDocument.objects.filter(id=doc_id, user=user).first()
    if not profile_doc:
        return JsonResponse({"error": "Document not found."}, status=404)

    if ApplicationDocument.objects.filter(vault_document=profile_doc).exists():
        return JsonResponse(
            {
                "error": "Το δικαιολογητικό χρησιμοποιείται σε υποβλημένη αίτηση και δεν μπορεί να τροποποιηθεί.",
            },
            status=400,
        )
    if request.method == "PUT":
        new_file = request.FILES.get("file")
        validation_error = validate_vault_file(new_file, doc_type=profile_doc.doc_type)
        if validation_error:
            return JsonResponse({"error": validation_error}, status=400)

        if profile_doc.file:
            profile_doc.file.delete(save=False)
        profile_doc.file = new_file
        profile_doc.uploaded_at = timezone.now()
        profile_doc.save(update_fields=["file", "uploaded_at"])

        return JsonResponse(profile_doc_info(profile_doc), safe=False)

    if request.method == "DELETE":
        doc_type = profile_doc.doc_type
        was_default = profile_doc.is_default
        degrees = list(
            PhdDegree.objects.filter(
                models.Q(vault_document=profile_doc) | models.Q(doatap_document=profile_doc)
            )
        )
        for degree in degrees:
            update_fields = []
            if degree.vault_document_id == profile_doc.id:
                degree.vault_document = None
                update_fields.append("vault_document")
            if degree.doatap_document_id == profile_doc.id:
                degree.doatap_document = None
                update_fields.append("doatap_document")
            if update_fields:
                degree.save(update_fields=update_fields)
        if profile_doc.file:
            profile_doc.file.delete(save=False)
        profile_doc.delete()

        if doc_type in SINGLE_DOC_TYPES and was_default:
            replacement = (
                VaultDocument.objects.filter(user=user, doc_type=doc_type)
                .order_by("-uploaded_at", "-id")
                .first()
            )
            if replacement:
                ensure_single_default(user, doc_type, keep_id=replacement.id)
                if not replacement.is_default:
                    replacement.is_default = True
                    replacement.save(update_fields=["is_default"])

        return JsonResponse({"status": "deleted"}, status=200)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def profile_document_create(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    doc_type = request.data.get("docType")
    if doc_type not in SINGLE_DOC_TYPES and doc_type not in MULTI_DOC_TYPES:
        return JsonResponse({"error": "Invalid document type."}, status=400)

    new_file = request.FILES.get("file")
    validation_error = validate_vault_file(new_file, doc_type=doc_type)
    if validation_error:
        return JsonResponse({"error": validation_error}, status=400)

    profile_doc = VaultDocument.objects.create(
        user=user,
        doc_type=doc_type,
        file=new_file,
        is_default=True,
    )
    if doc_type in SINGLE_DOC_TYPES:
        ensure_single_default(user, doc_type, keep_id=profile_doc.id)

    return JsonResponse(profile_doc_info(profile_doc), safe=False)


# Handle Form Submission
def process_publication(publication):
    if publication.get("type") == "journal":
        return get_sjr_quartile(publication.get("year"), publication.get("issn"))
    return None


def normalize_publication_value(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_authors_value(value):
    if isinstance(value, list):
        return ", ".join([normalize_publication_value(author) for author in value if normalize_publication_value(author)])
    return normalize_publication_value(value)


def build_profile_publication_payload(data):
    return {
        "type": normalize_publication_value(data.get("type")),
        "publication_title": normalize_publication_value(data.get("publicationTitle")),
        "journal_conf_title": normalize_publication_value(data.get("journalConfTitle")),
        "year": normalize_publication_value(data.get("year")),
        "issn": normalize_publication_value(data.get("issn")),
        "country": normalize_publication_value(data.get("country")),
        "quartile": normalize_publication_value(data.get("quartile")),
        "authors": normalize_authors_value(data.get("authors")),
        "publisher": normalize_publication_value(data.get("publisher")),
    }


def profile_publication_key(payload):
    return (
        payload.get("type", ""),
        payload.get("publication_title", ""),
        payload.get("journal_conf_title", ""),
        payload.get("year", ""),
        payload.get("issn", ""),
        payload.get("country", ""),
        payload.get("quartile", ""),
        payload.get("authors", ""),
        payload.get("publisher", ""),
    )


def serialize_profile_publication(publication):
    return {
        "id": publication.id,
        "type": publication.type,
        "publicationTitle": publication.publication_title,
        "journalConfTitle": publication.journal_conf_title,
        "year": publication.year,
        "issn": publication.issn,
        "country": publication.country,
        "quartile": publication.quartile,
        "authors": publication.authors or "",
        "publisher": publication.publisher,
    }

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])  # Handle both form data and file uploads
@csrf_exempt
def handle_form_submission(request):

    # 1. Get JWT token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    # 2. Decode token to get user_id
    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)
    user_id = payload.get("user_id")

    # 3. Fetch user
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    
    # 4. Update user role to "applicant" if not already
    if user.role != "applicant":
        user.role = "applicant"
        user.save()

    # 5. Process form submission
    if request.method == 'POST':
        start_time = time.time()
        try:
            form_data = request.data
            submission_id = form_data.get("submissionId")
            set_submission_progress(submission_id, user_id, 15, "Έλεγχος στοιχείων")
            publications_json = form_data.get("publications", "[]")
            publications = json.loads(publications_json)
            course_plans_json = form_data.get("coursePlans", "{}")
            try:
                course_plans_payload = (
                    json.loads(course_plans_json)
                    if isinstance(course_plans_json, str)
                    else course_plans_json
                )
            except json.JSONDecodeError:
                return JsonResponse(
                    {"error": "Τα στοιχεία σχεδιαγράμματος μαθημάτων δεν είναι έγκυρα."},
                    status=400,
                )
            if not isinstance(course_plans_payload, dict):
                return JsonResponse(
                    {"error": "Τα στοιχεία σχεδιαγράμματος μαθημάτων δεν είναι έγκυρα."},
                    status=400,
                )

            def parse_keywords(value):
                if value is None:
                    return []
                if isinstance(value, list):
                    items = [str(item).strip() for item in value if str(item).strip()]
                elif isinstance(value, str):
                    if value.strip() == "":
                        items = []
                    else:
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                items = [str(item).strip() for item in parsed if str(item).strip()]
                            else:
                                items = [value.strip()]
                        except json.JSONDecodeError:
                            items = [value.strip()]
                if not isinstance(value, (list, str)):
                    items = [str(value).strip()] if str(value).strip() else []
                deduped = []
                seen = set()
                for item in items:
                    key = item.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(item)
                return deduped

            def count_words(text):
                return len([word for word in str(text or "").split() if word.strip()])

            def normalize_authors(value):
                if isinstance(value, list):
                    return ", ".join([str(author).strip() for author in value if str(author).strip()])
                if value is None:
                    return ""
                return str(value)


            # --- Require position for unique application ---
            position_id = form_data.get("positionId")
            if not position_id or str(position_id).lower() in {"", "null", "none"}:
                return JsonResponse({"error": "Position is required."}, status=400)

            try:
                position = Position.objects.get(id=position_id)
            except Position.DoesNotExist:
                return JsonResponse({"error": "Position not found."}, status=404)

            if not is_position_active(position):
                return JsonResponse({"error": "Η θέση δεν είναι ενεργή για υποβολή/επανυποβολή."}, status=400)

            position_courses = list(position.scientific_field.courses.all())
            if not position_courses:
                return JsonResponse(
                    {"error": "Δεν βρέθηκαν μαθήματα για την επιλεγμένη θέση."},
                    status=400,
                )

            normalized_course_plans = {}
            for course in position_courses:
                plan_payload = course_plans_payload.get(str(course.id))
                if not isinstance(plan_payload, dict):
                    return JsonResponse(
                        {
                            "error": (
                                f"Συμπληρώστε όλα τα πεδία σχεδιαγράμματος για το μάθημα \"{course.name}\"."
                            )
                        },
                        status=400,
                    )

                normalized_plan = {}
                for api_field, db_field in COURSE_PLAN_FIELDS_MAP.items():
                    value = (plan_payload.get(api_field) or "").strip()
                    if not value:
                        return JsonResponse(
                            {
                                "error": (
                                    f"Το πεδίο \"{api_field}\" είναι υποχρεωτικό για το μάθημα \"{course.name}\"."
                                )
                            },
                            status=400,
                        )
                    normalized_plan[db_field] = value

                normalized_course_plans[course.id] = normalized_plan

            # --- Get or create Application ---
            application, created = Application.objects.get_or_create(
                user=user,
                position=position,
            )
            set_submission_progress(submission_id, user_id, 35, "Αποθήκευση στοιχείων αίτησης")
            previous_snapshot = None
            if not created:
                previous_snapshot = build_application_snapshot(application)

            # --- Update simple fields ---
            application.phone_number = form_data.get("phoneNumber")
            application.landline_number = form_data.get("landlineNumber")
            application.street_address = form_data.get("streetAddress")
            application.city = form_data.get("city")
            application.postal_code = form_data.get("postalCode")
            application.is_public_employee = form_data.get("isPublicEmployee") == "true"
            application.phd_title = form_data.get("phdTitle")
            application.phd_acquisition_date = form_data.get("phdAcquisitionDate")
            application.phd_is_from_foreign_institute = form_data.get("phdIsFromForeignInstitute") == "true"
            application.phd_abstract = (form_data.get("phdAbstract") or "").strip()
            application.phd_keywords = parse_keywords(form_data.get("phdKeywords"))

            if not application.phd_abstract:
                return JsonResponse({"error": "Το πεδίο περίληψης είναι υποχρεωτικό."}, status=400)
            abstract_word_count = count_words(application.phd_abstract)
            if abstract_word_count < PHD_ABSTRACT_MIN_WORDS:
                return JsonResponse(
                    {
                        "error": (
                            f"Η περίληψη πρέπει να έχει τουλάχιστον {PHD_ABSTRACT_MIN_WORDS} λέξεις."
                        )
                    },
                    status=400,
                )
            if abstract_word_count > PHD_ABSTRACT_MAX_WORDS:
                return JsonResponse(
                    {
                        "error": (
                            f"Η περίληψη δεν μπορεί να ξεπερνά τις {PHD_ABSTRACT_MAX_WORDS} λέξεις."
                        )
                    },
                    status=400,
                )
            if not application.phd_keywords:
                return JsonResponse({"error": "Οι λέξεις-κλειδιά είναι υποχρεωτικές."}, status=400)
            if len(application.phd_keywords) < PHD_KEYWORDS_MIN:
                return JsonResponse(
                    {
                        "error": (
                            f"Οι λέξεις-κλειδιά πρέπει να είναι τουλάχιστον {PHD_KEYWORDS_MIN}."
                        )
                    },
                    status=400,
                )
            if len(application.phd_keywords) > PHD_KEYWORDS_MAX:
                return JsonResponse(
                    {
                        "error": (
                            f"Οι λέξεις-κλειδιά δεν μπορούν να είναι πάνω από {PHD_KEYWORDS_MAX}."
                        )
                    },
                    status=400,
                )

            phd_degree_id = form_data.get("phdDegreeId")

            application.position = position

            application.work_experience = int(form_data.get("workExperience", 0))
            application.has_not_participated_in_past_program = form_data.get("hasNotParticipatedInPastProgram") == "true"
            application.is_eu_citizen_non_greek = form_data.get("isEuCitizenNonGreek") == "true"

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.mobile_number = application.phone_number
            profile.landline_number = application.landline_number
            profile.street_address = application.street_address
            profile.city = application.city
            profile.postal_code = application.postal_code
            profile.is_public_employee = application.is_public_employee
            profile.is_eu_citizen_non_greek = application.is_eu_citizen_non_greek
            profile.has_not_participated_in_past_program = application.has_not_participated_in_past_program
            profile.work_experience = application.work_experience
            profile.save()

            set_submission_progress(submission_id, user_id, 55, "Επεξεργασία εγγράφων")

            def handle_profile_doc_upload(field_key, doc_type):
                new_file = request.FILES.get(field_key)
                doc_id_key = f"{field_key}Id"
                doc_id_value = form_data.get(doc_id_key)

                if new_file:
                    validation_error = validate_vault_file(new_file, doc_type=doc_type)
                    if validation_error:
                        raise ValueError(validation_error)
                    profile_doc = VaultDocument(
                        user=user,
                        doc_type=doc_type,
                        file=new_file,
                        is_default=True,
                    )
                    profile_doc.application_id = application.id
                    profile_doc.save()
                    if doc_type in SINGLE_DOC_TYPES:
                        ensure_single_default(user, doc_type, keep_id=profile_doc.id)

                    ApplicationDocument.objects.filter(
                        application=application,
                        doc_type=doc_type,
                    ).delete()
                    ApplicationDocument.objects.create(
                        application=application,
                    vault_document=profile_doc,
                        doc_type=doc_type,
                    )
                    return profile_doc

                if doc_id_value is None:
                    return None

                if str(doc_id_value).strip() == "":
                    links = ApplicationDocument.objects.filter(
                        application=application,
                        doc_type=doc_type,
                    )
                    for link in links:
                        profile_doc = link.vault_document
                        link.delete()
                        cleanup_profile_doc_if_orphan(profile_doc)
                    return None

                profile_doc = VaultDocument.objects.filter(
                    id=doc_id_value,
                    user=user,
                    doc_type=doc_type,
                ).first()
                if profile_doc:
                    ensure_doc_in_application_folder(profile_doc, application.id)
                    ApplicationDocument.objects.filter(
                        application=application,
                        doc_type=doc_type,
                    ).delete()
                    ApplicationDocument.objects.create(
                        application=application,
                        vault_document=profile_doc,
                        doc_type=doc_type,
                    )
                return profile_doc

            phd_vault_doc = None
            doatap_vault_doc = None
            for field_key, doc_type in PROFILE_DOC_FIELD_MAP.items():
                selected_doc = handle_profile_doc_upload(field_key, doc_type)
                if doc_type == "phd":
                    phd_vault_doc = selected_doc
                elif doc_type == "doatap":
                    doatap_vault_doc = selected_doc

            if not phd_vault_doc:
                return JsonResponse({"error": "Το διδακτορικό έγγραφο είναι υποχρεωτικό."}, status=400)
            if application.phd_is_from_foreign_institute and not doatap_vault_doc:
                return JsonResponse({"error": "Το έγγραφο ΔΟΑΤΑΠ είναι υποχρεωτικό."}, status=400)

            degree = None
            linked_degree = None
            if phd_degree_id not in {None, "", "null", "None"}:
                try:
                    linked_degree = PhdDegree.objects.filter(
                        id=int(phd_degree_id), user=user
                    ).first()
                except (TypeError, ValueError):
                    linked_degree = None

            if linked_degree is None and application.phd_degree_id:
                linked_degree = PhdDegree.objects.filter(
                    id=application.phd_degree_id, user=user
                ).first()

            degree = linked_degree
            title_value = (application.phd_title or "").strip()
            phd_doc_id = phd_vault_doc.id if phd_vault_doc else None
            base_degree = degree
            title_changed = False
            file_changed = False
            create_new = False
            if degree:
                title_changed = title_value != (degree.title or "")
                file_changed = phd_doc_id != degree.vault_document_id
                if title_changed and file_changed:
                    degree = PhdDegree(user=user)
                    create_new = True
            elif title_value and application.phd_acquisition_date and phd_vault_doc:
                degree = PhdDegree(user=user)
                create_new = True

            if degree:
                degree.title = title_value
                degree.acquired_at = application.phd_acquisition_date
                degree.is_foreign_institute = application.phd_is_from_foreign_institute
                degree.abstract = application.phd_abstract or ""
                degree.keywords = application.phd_keywords or []
                if phd_vault_doc:
                    degree.vault_document = phd_vault_doc
                if degree.is_foreign_institute:
                    if doatap_vault_doc:
                        degree.doatap_document = doatap_vault_doc
                else:
                    degree.doatap_document = None
                degree.save()
                application.phd_degree = degree

            application.save()

            existing_course_plans = {
                plan.course_id: plan
                for plan in CoursePlan.objects.filter(
                    application=application,
                    course_id__in=[course.id for course in position_courses],
                )
            }

            for course in position_courses:
                course_plan = existing_course_plans.get(course.id)
                if not course_plan:
                    course_plan = CoursePlan(application=application, course=course)

                for field_name, field_value in normalized_course_plans[course.id].items():
                    setattr(course_plan, field_name, field_value)

                course_plan.save()

            CoursePlan.objects.filter(application=application).exclude(
                course_id__in=[course.id for course in position_courses]
            ).delete()

            relevance_progress_label = "Αξιολόγηση συνάφειας αίτησης με επιστημονικό πεδίο"
            ai_jobs = []
            if degree and application.phd_title and application.phd_abstract:
                ai_jobs.append(
                    (
                        process_phd_ai_job,
                        (application.id, submission_id, user_id, relevance_progress_label),
                    )
                )

            ai_jobs.append(
                (
                    process_course_plan_ai_job,
                    (application.id, submission_id, user_id, relevance_progress_label),
                )
            )

            if ai_jobs:
                set_submission_progress(submission_id, user_id, 68, relevance_progress_label)
                with ThreadPoolExecutor(max_workers=min(2, len(ai_jobs))) as executor:
                    futures = [executor.submit(job_func, *job_args) for job_func, job_args in ai_jobs]
                    for future in futures:
                        future.result()

            def handle_multi_docs(field_key, doc_type, keep_ids_key=None):
                new_files = request.FILES.getlist(field_key)
                keep_ids = None
                if keep_ids_key and form_data.get(keep_ids_key):
                    try:
                        keep_ids = set(json.loads(form_data.get(keep_ids_key, "[]")))
                    except json.JSONDecodeError:
                        keep_ids = None

                if keep_ids is not None:
                    links = ApplicationDocument.objects.filter(
                        application=application,
                        doc_type=doc_type,
                    )
                    for link in links.exclude(vault_document_id__in=keep_ids):
                        profile_doc = link.vault_document
                        link.delete()
                        cleanup_profile_doc_if_orphan(profile_doc)

                    existing_ids = set(links.values_list("vault_document_id", flat=True))
                    missing_ids = keep_ids - existing_ids
                    if missing_ids:
                        for doc in VaultDocument.objects.filter(
                            id__in=missing_ids, user=user, doc_type=doc_type
                        ):
                            ensure_doc_in_application_folder(doc, application.id)
                            ApplicationDocument.objects.create(
                                application=application,
                                vault_document=doc,
                                doc_type=doc_type,
                            )

                for doc_file in new_files:
                    if not doc_file:
                        continue
                    profile_doc = VaultDocument(
                        user=user,
                        doc_type=doc_type,
                        file=doc_file,
                        is_default=True,
                    )
                    profile_doc.application_id = application.id
                    profile_doc.save()
                    ApplicationDocument.objects.create(
                        application=application,
                        vault_document=profile_doc,
                        doc_type=doc_type,
                    )

            handle_multi_docs(
                "bioSupportingDocuments",
                "bio_supporting",
                keep_ids_key="bioSupportingDocumentIds",
            )
            handle_multi_docs(
                "employmentCertificateDocuments",
                "employment_certificate",
                keep_ids_key="employmentCertificateDocumentIds",
            )

            set_submission_progress(submission_id, user_id, 86, "Επεξεργασία δημοσιεύσεων (SJR)")

            # --- Publications resubmission logic ---
            # Build a dict of existing publications for quick lookup
            existing_publications = {publication.id: publication for publication in application.publications.all()}
            submitted_ids = set()

            # SJR results and multithreading
            sjr_results = []
            with ThreadPoolExecutor(max_workers=4) as executor: 
                future_to_publication = {executor.submit(process_publication, publication): publication for publication in publications}
                total_publications = len(future_to_publication)
                completed_publications = 0

                for future in future_to_publication:
                    publication = future_to_publication[future]
                    sjr_data = future.result()
                    completed_publications += 1
                    if total_publications:
                        percent = 86 + int((completed_publications / total_publications) * 10)
                        set_submission_progress(
                            submission_id,
                            user_id,
                            percent,
                            "Επεξεργασία δημοσιεύσεων (SJR)",
                            detail=f"{completed_publications}/{total_publications}",
                        )

                    notFound = ""
                    sjr_results.append({
                        "journalTitle": sjr_data["title"] if sjr_data else publication.get("journalConfTitle", notFound),
                        # "year": sjr_data["year"] if sjr_data else publication.get("year", notFound),
                        "issn": (
                            publication.get("issn") if sjr_data
                            else (
                                notFound if not publication.get("issn") or publication.get("issn") == notFound
                                else (
                                    publication.get("issn") if "Wrong" in publication.get("issn")
                                    else publication.get("issn") + " (Wrong)"
                                )
                            )
                        ),
                        "country": sjr_data["country"] if sjr_data else notFound,
                        "sjr_quartile": sjr_data["sjr_quartile"] if sjr_data else notFound,
                    })

                    sjr_result = sjr_results[-1]

                    publication_id = publication.get("id")
                    if publication_id and publication_id in existing_publications:
                        # Update existing publication
                        db_publication = existing_publications[publication_id]
                        db_publication.type = publication.get("type")
                        db_publication.publication_title = publication.get("publicationTitle")
                        db_publication.journal_conf_title = sjr_result["journalTitle"]
                        db_publication.year = publication.get("year")
                        db_publication.issn = sjr_result["issn"]
                        db_publication.country = sjr_result["country"]
                        db_publication.quartile = sjr_result["sjr_quartile"]
                        db_publication.authors = normalize_authors(publication.get("authors"))
                        db_publication.publisher = publication.get("publisher")
                        db_publication.save()
                        submitted_ids.add(publication_id)
                    else:
                        # Create new publication
                        new_publication = Publication.objects.create(
                            application=application,
                            type=publication.get("type"),
                            publication_title=publication.get("publicationTitle"),
                            journal_conf_title=sjr_result["journalTitle"],
                            year=publication.get("year"),
                            issn=sjr_result["issn"],
                            country=sjr_result["country"],
                            quartile=sjr_result["sjr_quartile"],
                            authors=normalize_authors(publication.get("authors")),
                            publisher=publication.get("publisher"),
                        )
                        submitted_ids.add(new_publication.id)

            # Delete publications not in submitted
            for publication_id, db_publication in existing_publications.items():
                if publication_id not in submitted_ids:
                    db_publication.delete()

            if created:
                existing_profile_publications = list(
                    ProfilePublication.objects.filter(user=user)
                )
                existing_keys = {
                    profile_publication_key(
                        {
                            "type": normalize_publication_value(pub.type),
                            "publication_title": normalize_publication_value(pub.publication_title),
                            "journal_conf_title": normalize_publication_value(pub.journal_conf_title),
                            "year": normalize_publication_value(pub.year),
                            "issn": normalize_publication_value(pub.issn),
                            "country": normalize_publication_value(pub.country),
                            "quartile": normalize_publication_value(pub.quartile),
                            "authors": normalize_authors_value(pub.authors),
                            "publisher": normalize_publication_value(pub.publisher),
                        }
                    )
                    for pub in existing_profile_publications
                }
                added_keys = set()
                for publication in publications:
                    payload = build_profile_publication_payload(publication or {})
                    key = profile_publication_key(payload)
                    if key in existing_keys or key in added_keys:
                        continue
                    ProfilePublication.objects.create(
                        user=user,
                        type=payload["type"] or None,
                        publication_title=payload["publication_title"] or None,
                        journal_conf_title=payload["journal_conf_title"] or None,
                        year=payload["year"] or None,
                        issn=payload["issn"] or None,
                        country=payload["country"] or None,
                        quartile=payload["quartile"] or None,
                        authors=payload["authors"] or "",
                        publisher=payload["publisher"] or None,
                    )
                    added_keys.add(key)

            # Retrieve all Publication instances for the application
            publications_qs = Publication.objects.filter(application=application)

            # Now calculate points AFTER publications are processed
            set_submission_progress(submission_id, user_id, 97, "Υπολογισμός μορίων")
            calculated_points = calculate_points(application, publications_qs)
            
            # Update the Application instance with the calculated points
            Application.objects.filter(id=application.id).update(**calculated_points)

            if created:
                set_submission_progress(submission_id, user_id, 99, "Αποστολή ειδοποίησης")
                submission_context = {
                    "scientific_field": position.scientific_field.name,
                    "end_date": position.end_date.strftime("%d-%m-%Y"),
                    "application_id": application.id,
                }
                try:
                    send_template_email_async(
                        "application_submitted",
                        user.email,
                        submission_context,
                    )
                except Exception as exc:
                    print(f"Submission email failed: {exc}")
            else:
                current_snapshot = build_application_snapshot(application)
                changed, _, _ = diff_application_snapshots(
                    previous_snapshot,
                    current_snapshot,
                )
                if changed:
                    set_submission_progress(submission_id, user_id, 99, "Αποστολή ειδοποίησης")
                    resubmission_context = {
                        "scientific_field": position.scientific_field.name,
                        "end_date": position.end_date.strftime("%d-%m-%Y"),
                        "application_id": application.id,
                    }
                    try:
                        send_template_email_async(
                            "application_resubmitted",
                            user.email,
                            resubmission_context,
                        )
                    except Exception as exc:
                        print(f"Resubmission email failed: {exc}")

            # Serialize the application instance
            application_serializer = ApplicationSerializer(application)

            end_time = time.time()
            execution_time = end_time - start_time
            print(f"⏱️ Total execution time: {execution_time:.4f} seconds\n")

            set_submission_progress(submission_id, user_id, 100, "Ολοκληρώθηκε", done=True)

            return JsonResponse({
                'message': 'Success',
                # 'sjr_results': sjr_results,
                # 'application': application_serializer.data
            }, status=200)

        except Exception as e:
            set_submission_progress(submission_id, user_id, 100, "Αποτυχία", done=True, error=str(e))
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(["GET"])
def get_submit_progress(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")

    submission_id = request.GET.get("submissionId")
    if not submission_id:
        return JsonResponse({"error": "submissionId is required."}, status=400)

    debug = request.GET.get("debug") in {"1", "true", "True"}

    cached = cache.get(submission_progress_key(submission_id))
    if not cached:
        response = {"percent": 0, "label": "Σε αναμονή", "done": False}
        if debug:
            response["debug"] = {
                "submissionId": submission_id,
                "cachePresent": False,
            }
        return JsonResponse(response, status=200)
    if cached.get("userId") != user_id:
        return JsonResponse({"error": "Not found."}, status=404)

    response = {k: v for k, v in cached.items() if k != "userId"}
    if debug:
        response["debug"] = {
            "submissionId": submission_id,
            "cachePresent": True,
            "cachePayload": response,
        }
    return JsonResponse(response, status=200)

# Get Applicant Score
@api_view(["GET"])
def get_applicant_score(request, application_id):
    # Check for Bearer token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    # Decode token and get user
    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    requesting_user = User.objects.filter(id=user_id).first()
    if not requesting_user:
        return JsonResponse({"error": "User not found"}, status=404)

    application = get_object_or_404(
        Application.objects.select_related("position", "position__scientific_field"),
        id=application_id,
    )

    if requesting_user.role != "admin" and requesting_user.id != application.user_id:
        return JsonResponse({"error": "Forbidden."}, status=403)
    user = application.user
    sf = application.position.scientific_field if application.position else None
    course_plans = {
        str(course_plan.course_id): {
            "generalDescription": course_plan.general_description or "",
            "learningObjectives": course_plan.learning_objectives or "",
            "courseSchedule": course_plan.course_schedule or "",
            "deliveryMethods": course_plan.delivery_methods or "",
            "bibliographyMaterial": course_plan.bibliography_material or "",
            "learningOutcomes": course_plan.learning_outcomes or "",
            "assessmentMethodsCriteria": course_plan.assessment_methods_criteria or "",
        }
        for course_plan in CoursePlan.objects.filter(application=application)
    }

    def file_info(file_field, key):
        if not file_field:
            return {"url": None, "name": None, "downloadPath": None}
        download_path = f"/api/applicant/{application.id}/documents/{key}"
        return {
            "url": request.build_absolute_uri(file_field.url),
            "name": file_field.name.split("/")[-1],
            "downloadPath": download_path,
        }

    single_docs, multi_docs, has_links = build_application_document_maps(application)

    def linked_doc_info(doc_type):
        if has_links and doc_type in single_docs:
            doc_id = single_docs[doc_type]["id"]
            vault_doc = VaultDocument.objects.filter(id=doc_id).first()
            if vault_doc and vault_doc.file:
                return {
                    "url": request.build_absolute_uri(vault_doc.file.url),
                    "name": os.path.basename(vault_doc.file.name),
                    "downloadPath": f"/api/applicant/{application.id}/documents/{doc_id}",
                }
        return {"url": None, "name": None, "downloadPath": None}

    data = {
        "id": user.id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "phdTitle": application.phd_title,
        "phdAcquisitionDate": application.phd_acquisition_date.strftime("%d-%m-%Y") if application.phd_acquisition_date else "",
        "phdAbstract": application.phd_abstract or "",
        "phdKeywords": application.phd_keywords or [],
        "scientificField": sf.name if sf else "",
        "school": get_school_of_department(sf.department) if sf else "",
        "department": sf.department if sf else "",
        "courses": [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "description": c.description,
                "semester": c.semester,
                "teachingUnits": c.teaching_units,
                "ects": c.ects,
                "theory_hours": c.theory_hours,
                "lab_hours": c.lab_hours,
                "category": c.category,
            }
            for c in (sf.courses.all() if sf else [])
        ],
        "workExperience": application.work_experience,
        "coursePlanRelevancePoints": application.course_plan_relevance_points,
        "courseMaterialStructurePoints": application.course_material_structure_points,
        "thesisRelevancePoints": application.thesis_relevance_points,
        "publicationPoints": application.publication_points,
        "workExperiencePoints": application.work_experience_points,
        "notPastProgramPoints": application.not_past_program_points,
        "totalPoints": application.total_points,
        "publications": [
            {
                "id": publication.id,
                "type": publication.type,
                "publicationTitle": publication.publication_title,
                "journalConfTitle": publication.journal_conf_title,
                "year": publication.year,
                "issn": publication.issn,
                "country": publication.country,
                "quartile": publication.quartile,
                "authors": publication.authors or "",
                "publisher": publication.publisher,
            }
            for publication in application.publications.all()
        ],
        "submitDate": timezone.localtime(application.submitted_at, ZoneInfo("Europe/Athens")).strftime("%d-%m-%Y %H:%M") if application.submitted_at else "",
        "positionStartDate": application.position.start_date.strftime("%d-%m-%Y") if application.position and application.position.start_date else "",
        "positionEndDate": application.position.end_date.strftime("%d-%m-%Y") if application.position and application.position.end_date else "",
        "positionStartTime": application.position.start_time.strftime("%H:%M") if application.position and application.position.start_time else "",
        "positionEndTime": application.position.end_time.strftime("%H:%M") if application.position and application.position.end_time else "",
        "documents": {
            "cv": linked_doc_info("cv"),
            "bioSupportingDocuments": multi_docs.get("bio_supporting", []) if has_links else [],
            "phd": linked_doc_info("phd"),
            "doatap": linked_doc_info("doatap"),
            "coursePlan": linked_doc_info("course_plan"),
            "military": linked_doc_info("military"),
            "employmentCertificates": multi_docs.get("employment_certificate", []) if has_links else [],
            "publicEmployeePermission": linked_doc_info("public_employee_permission"),
            "notParticipatedDeclaration": linked_doc_info("not_participated_declaration"),
            "euCitizenGreekLanguageCertificate": linked_doc_info(
                "eu_citizen_greek_language_certificate"
            ),
            "responsibleDeclaration": linked_doc_info("responsible_declaration"),
        },
        "coursePlans": course_plans,
    }
    return JsonResponse(data, safe=False)


@api_view(["GET"])
def get_application_detail(request, application_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    requesting_user = User.objects.filter(id=user_id).first()
    if not requesting_user:
        return JsonResponse({"error": "User not found"}, status=404)

    application = get_object_or_404(
        Application.objects.select_related("position", "position__scientific_field"),
        id=application_id,
    )

    if requesting_user.role != "admin" and requesting_user.id != application.user_id:
        return JsonResponse({"error": "Forbidden."}, status=403)

    data = build_application_form(application)
    return JsonResponse(data, safe=False)


@api_view(["DELETE"])
def delete_application(request, application_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    requesting_user = User.objects.filter(id=user_id).first()
    if not requesting_user:
        return JsonResponse({"error": "User not found"}, status=404)

    application = get_object_or_404(
        Application.objects.select_related("position"),
        id=application_id,
    )
    application_user_id = application.user_id

    if requesting_user.role != "admin" and requesting_user.id != application.user_id:
        return JsonResponse({"error": "Forbidden."}, status=403)

    if not is_position_active(application.position):
        return JsonResponse({"error": "Η θέση δεν είναι ενεργή για διαγραφή."}, status=400)

    links = list(
        ApplicationDocument.objects.filter(application=application).select_related("vault_document")
    )
    degree = application.phd_degree
    has_other_degree_refs = False
    if degree:
        has_other_degree_refs = Application.objects.filter(phd_degree=degree).exclude(id=application.id).exists()

    application.delete()

    for link in links:
        cleanup_profile_doc_if_orphan(link.vault_document)

    if degree and not has_other_degree_refs:
        degree_docs = [degree.vault_document, degree.doatap_document]
        degree.vault_document = None
        degree.doatap_document = None
        degree.save(update_fields=["vault_document", "doatap_document"])
        for doc in degree_docs:
            cleanup_profile_doc_if_orphan(doc)

    if application_user_id:
        app_dir = os.path.join(
            settings.MEDIA_ROOT,
            f"documents/user_{application_user_id}/application_{application_id}",
        )
        try:
            if os.path.isdir(app_dir) and not os.listdir(app_dir):
                os.rmdir(app_dir)
        except OSError:
            pass

    return JsonResponse({"success": True})


@api_view(["GET"])
def download_applicant_document(request, application_id, doc_key):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    user_id = payload.get("user_id")
    requesting_user = User.objects.filter(id=user_id).first()
    if not requesting_user:
        return JsonResponse({"error": "User not found"}, status=404)

    application = get_object_or_404(Application, id=application_id)

    if requesting_user.role != "admin" and requesting_user.id != application.user_id:
        return JsonResponse({"error": "Forbidden."}, status=403)
    file_field = None
    if str(doc_key).isdigit():
        link = ApplicationDocument.objects.filter(
            application=application,
            vault_document_id=int(doc_key),
        ).select_related("vault_document").first()
        file_field = link.vault_document.file if link else None
    else:
        doc_key_map = {
            "cv": "cv",
            "phd": "phd",
            "doatap": "doatap",
            "coursePlan": "course_plan",
            "military": "military",
            "publicEmployeePermission": "public_employee_permission",
            "notParticipatedDeclaration": "not_participated_declaration",
            "euCitizenGreekLanguageCertificate": "eu_citizen_greek_language_certificate",
            "responsibleDeclaration": "responsible_declaration",
        }
        doc_type = doc_key_map.get(str(doc_key), str(doc_key))
        link = ApplicationDocument.objects.filter(
            application=application,
            doc_type=doc_type,
        ).select_related("vault_document").first()
        file_field = link.vault_document.file if link else None

    if not file_field or not file_field.name:
        return JsonResponse({"error": "Document not found."}, status=404)

    filename = os.path.basename(file_field.name)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    inline = request.GET.get("inline") in {"1", "true", "True"}
    response = FileResponse(
        file_field.open("rb"),
        as_attachment=not inline,
        filename=filename,
        content_type=content_type,
    )
    return response

# Get All Scores
@api_view(["GET"])
def get_all_scores(request):
    # Get user and role from token
    auth_header = request.headers.get("Authorization")
    user_role = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt(token)
        if payload:
            user_id = payload.get("user_id")
            user = User.objects.filter(id=user_id).first()
            if user:
                user_role = user.role

    applicants = User.objects.filter(role="applicant")
    result = []
    tz = ZoneInfo("Europe/Athens")
    now = timezone.now().astimezone(tz)
    for user in applicants:
        applications = user.applications.select_related("position", "position__scientific_field").all()
        for app in applications:
            if not app.position or not app.position.scientific_field:
                continue
            include = True
            if user_role in ["applicant", "guest"]:
                if not app.position or not app.position.end_date:
                    include = False
                else:
                    end_t = app.position.end_time or dt_time(23, 59)
                    end_dt = datetime.combine(app.position.end_date, end_t, tzinfo=tz)
                    if end_dt >= now:
                        include = False
            if not include:
                continue

            if hasattr(app, "submitted_at") and app.submitted_at:
                submit_date = timezone.localtime(app.submitted_at, tz).strftime("%d-%m-%Y %H:%M")
            else:
                submit_date = ""
            result.append({
                "id": user.id,
                "applicationId": app.id,
                "positionId": app.position.id if app.position else None,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "school": get_school_of_department(app.position.scientific_field.department),
                "department": app.position.scientific_field.department,
                "scientificField": app.position.scientific_field.name,
                "submitDate": submit_date,
                "positionStartDate": app.position.start_date.strftime("%d-%m-%Y") if app.position and app.position.start_date else "",
                "positionEndDate": app.position.end_date.strftime("%d-%m-%Y") if app.position and app.position.end_date else "",
                "positionStartTime": app.position.start_time.strftime("%H:%M") if app.position and app.position.start_time else "",
                "positionEndTime": app.position.end_time.strftime("%H:%M") if app.position and app.position.end_time else "",
                "totalPoints": app.total_points,
            })
    return JsonResponse(result, safe=False)

# Scientific Fields collection (list + create)
@csrf_exempt
@api_view(["GET", "POST"])
def scientific_fields_collection(request):
    # Require Bearer token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)

    if request.method == "GET":
        sfs = ScientificField.objects.select_related("position").prefetch_related("courses", "position__applications")
        available_for_position = request.query_params.get("availableForPosition")
        tz = ZoneInfo("Europe/Athens")
        now = timezone.now().astimezone(tz)

        def compute_state(start_date, end_date, start_time, end_time):
            if not start_date or not end_date:
                return "pending"
            start_t = start_time or dt_time(0, 0)
            end_t = end_time or dt_time(23, 59)
            start_dt = datetime.combine(start_date, start_t, tzinfo=tz)
            end_dt = datetime.combine(end_date, end_t, tzinfo=tz)
            if now < start_dt:
                return "pending"
            if now > end_dt:
                return "completed"
            return "active"

        def is_available(sf):
            pos = getattr(sf, "position", None)
            if not pos:
                return True
            return compute_state(pos.start_date, pos.end_date, pos.start_time, pos.end_time) == "completed"

        if available_for_position and str(available_for_position).lower() in {"1", "true", "yes"}:
            sfs = [sf for sf in sfs if is_available(sf)]

        data = []
        for sf in sfs:
            pos = getattr(sf, "position", None)
            if pos:
                state = compute_state(pos.start_date, pos.end_date, pos.start_time, pos.end_time)
                applications_count = pos.applications.count()
            else:
                state = "unpublished"
                applications_count = 0

            data.append(
                {
                    "id": sf.id,
                    "name": sf.name,
                    "department": sf.department,
                    "school": sf.school,
                    "createdAt": sf.created_at.isoformat() if sf.created_at else None,
                    "positionId": pos.id if pos else None,
                    "positionStartDate": pos.start_date if pos else None,
                    "positionEndDate": pos.end_date if pos else None,
                    "positionStartTime": pos.start_time.strftime("%H:%M") if pos and pos.start_time else None,
                    "positionEndTime": pos.end_time.strftime("%H:%M") if pos and pos.end_time else None,
                    "state": state,
                    "applications": applications_count,
                    "courses": [
                        {
                            "id": course.id,
                            "name": course.name,
                            "code": course.code,
                            "description": course.description,
                            "semester": course.semester,
                            "teachingUnits": course.teaching_units,
                            "ects": course.ects,
                            "theory_hours": course.theory_hours,
                            "lab_hours": course.lab_hours,
                            "category": course.category,
                        }
                        for course in sf.courses.all()
                    ],
                }
            )
        return JsonResponse(data, safe=False)

    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user or user.role != "admin":
        return JsonResponse({"error": "Only admins can create scientific fields."}, status=403)

    data = request.data
    name = data.get("name")
    school = data.get("school")
    department = data.get("department")
    courses_json = data.get("courses", "[]")
    try:
        courses = json.loads(courses_json) if isinstance(courses_json, str) else courses_json
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid courses JSON."}, status=400)

    if not name or not str(name).strip():
        return JsonResponse({"error": "Scientific field name is required."}, status=400)
    if not school or school == "select":
        return JsonResponse({"error": "School is required."}, status=400)
    if not department or department == "select":
        return JsonResponse({"error": "Department is required."}, status=400)
    if not isinstance(courses, list) or len(courses) == 0:
        return JsonResponse({"error": "At least one course is required."}, status=400)

    sci_field = ScientificField.objects.create(
        name=str(name).strip(),
        department=department,
        school=school,
    )

    source_text = build_scientific_field_source_text(name, courses)
    profile, created_profile = ScientificFieldProfile.objects.get_or_create(scientific_field=sci_field)
    profile.source_text = source_text
    profile.profile_text = source_text
    if created_profile:
        profile.save()
    else:
        profile.save(update_fields=["source_text", "profile_text"])

    for course in courses:
        Course.objects.create(
            scientific_field=sci_field,
            code=course.get("code"),
            name=course.get("name"),
            description=course.get("description"),
            semester=course.get("semester"),
            teaching_units=course.get("teaching_units"),
            ects=course.get("ects"),
            theory_hours=course.get("theory_hours"),
            lab_hours=course.get("lab_hours"),
            category=course.get("category"),
        )

    process_scientific_field_ai_job(sci_field.id, source_text)

    return JsonResponse(
        {
            "message": "Scientific field created successfully.",
            "scientificFieldId": sci_field.id,
        },
        status=201,
    )


@api_view(["GET", "PUT", "DELETE"])
def scientific_field_detail(request, sf_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)

    sf = ScientificField.objects.select_related("position").prefetch_related("courses", "position__applications").filter(id=sf_id).first()
    if not sf:
        return JsonResponse({"error": "Scientific field not found."}, status=404)

    if request.method == "DELETE":
        user_id = payload.get("user_id")
        user = User.objects.filter(id=user_id).first()
        if not user or user.role != "admin":
            return JsonResponse({"error": "Only admins can delete scientific fields."}, status=403)
        sf.delete()
        return JsonResponse({"message": "Scientific field deleted successfully."}, status=200)

    if request.method == "PUT":
        user_id = payload.get("user_id")
        user = User.objects.filter(id=user_id).first()
        if not user or user.role != "admin":
            return JsonResponse({"error": "Only admins can update scientific fields."}, status=403)

        data = request.data
        name = data.get("name")
        school = data.get("school")
        department = data.get("department")
        courses_json = data.get("courses", "[]")

        try:
            courses = json.loads(courses_json) if isinstance(courses_json, str) else courses_json
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid courses JSON."}, status=400)

        if not name or not str(name).strip():
            return JsonResponse({"error": "Scientific field name is required."}, status=400)
        if not school or school == "select":
            return JsonResponse({"error": "School is required."}, status=400)
        if not department or department == "select":
            return JsonResponse({"error": "Department is required."}, status=400)
        if not isinstance(courses, list) or len(courses) == 0:
            return JsonResponse({"error": "At least one course is required."}, status=400)

        sf.name = str(name).strip()
        sf.school = school
        sf.department = department
        sf.save(update_fields=["name", "school", "department"])

        sf.courses.all().delete()
        for course in courses:
            Course.objects.create(
                scientific_field=sf,
                code=course.get("code"),
                name=course.get("name"),
                description=course.get("description"),
                semester=course.get("semester"),
                teaching_units=course.get("teaching_units"),
                ects=course.get("ects"),
                theory_hours=course.get("theory_hours"),
                lab_hours=course.get("lab_hours"),
                category=course.get("category"),
            )

        source_text = build_scientific_field_source_text(name, courses)
        profile, created_profile = ScientificFieldProfile.objects.get_or_create(scientific_field=sf)
        profile.source_text = source_text
        profile.profile_text = source_text
        if created_profile:
            profile.save()
        else:
            profile.save(update_fields=["source_text", "profile_text"])

        process_scientific_field_ai_job(sf.id, source_text)

        return JsonResponse(
            {
                "message": "Scientific field updated successfully.",
                "scientificFieldId": sf.id,
            },
            status=200,
        )

    tz = ZoneInfo("Europe/Athens")
    now = timezone.now().astimezone(tz)

    def compute_state(start_date, end_date, start_time, end_time):
        if not start_date or not end_date:
            return "pending"
        start_t = start_time or dt_time(0, 0)
        end_t = end_time or dt_time(23, 59)
        start_dt = datetime.combine(start_date, start_t, tzinfo=tz)
        end_dt = datetime.combine(end_date, end_t, tzinfo=tz)
        if now < start_dt:
            return "pending"
        if now > end_dt:
            return "completed"
        return "active"

    pos = getattr(sf, "position", None)
    if pos:
        state = compute_state(pos.start_date, pos.end_date, pos.start_time, pos.end_time)
        applications_count = pos.applications.count()
    else:
        state = "unpublished"
        applications_count = 0

    data = {
        "id": sf.id,
        "name": sf.name,
        "department": sf.department,
        "school": sf.school,
        "positionId": pos.id if pos else None,
        "positionStartDate": pos.start_date if pos else None,
        "positionEndDate": pos.end_date if pos else None,
        "positionStartTime": pos.start_time.strftime("%H:%M") if pos and pos.start_time else None,
        "positionEndTime": pos.end_time.strftime("%H:%M") if pos and pos.end_time else None,
        "state": state,
        "applications": applications_count,
        "courses": [
            {
                "id": course.id,
                "name": course.name,
                "code": course.code,
                "description": course.description,
                "semester": course.semester,
                "teachingUnits": course.teaching_units,
                "ects": course.ects,
                "theory_hours": course.theory_hours,
                "lab_hours": course.lab_hours,
                "category": course.category,
            }
            for course in sf.courses.all()
        ],
    }

    return JsonResponse(data, safe=False)

# Positions collection (list + create)
@csrf_exempt
@api_view(["GET", "POST"])
def positions_collection(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)
    if request.method == "GET":
        tz = ZoneInfo("Europe/Athens")
        now = timezone.now().astimezone(tz)
        positions = Position.objects.all()

        def compute_state(start_date, end_date, start_time, end_time):
            if not start_date or not end_date:
                return "pending"
            start_t = start_time or dt_time(0, 0)
            end_t = end_time or dt_time(23, 59)
            start_dt = datetime.combine(start_date, start_t, tzinfo=tz)
            end_dt = datetime.combine(end_date, end_t, tzinfo=tz)
            if now < start_dt:
                return "pending"
            if now > end_dt:
                return "completed"
            return "active"

        data = [
            {
                "id": pos.id,
                "scientificFieldId": pos.scientific_field.id,
                "scientificField": pos.scientific_field.name,
                "department": pos.scientific_field.department,
                "school": pos.scientific_field.school,
                "startDate": pos.start_date,
                "endDate": pos.end_date,
                "startTime": pos.start_time.strftime("%H:%M") if pos.start_time else None,
                "endTime": pos.end_time.strftime("%H:%M") if pos.end_time else None,
                "state": compute_state(pos.start_date, pos.end_date, pos.start_time, pos.end_time),
                "courses": [
                    {
                        "id": course.id,
                        "name": course.name,
                        "code": course.code,
                        "description": course.description,
                        "semester": course.semester,
                        "teachingUnits": course.teaching_units,
                        "ects": course.ects,
                        "theory_hours": course.theory_hours,
                        "lab_hours": course.lab_hours,
                        "category": course.category,
                    }
                    for course in pos.scientific_field.courses.all()
                ]
            }
            for pos in positions
        ]
        return JsonResponse(data, safe=False)

    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user or user.role != "admin":
        return JsonResponse({"error": "Only admins can create positions."}, status=403)

    data = request.data
    position_id = data.get("positionId")
    scientific_field_id = data.get("scientificFieldId")
    start_date = data.get("startDate")
    end_date = data.get("endDate")

    if not scientific_field_id:
        return JsonResponse({"error": "Scientific field id is required."}, status=400)
    if not start_date:
        return JsonResponse({"error": "Start date is required."}, status=400)
    if not end_date:
        return JsonResponse({"error": "End date is required."}, status=400)

    start_time_raw = data.get("startTime")
    end_time_raw = data.get("endTime")

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format."}, status=400)

    def parse_time(value, default_value):
        if value in [None, "", "null"]:
            return default_value
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None

    start_time_obj = parse_time(start_time_raw, dt_time(0, 0))
    end_time_obj = parse_time(end_time_raw, dt_time(23, 59))
    if start_time_obj is None or end_time_obj is None:
        return JsonResponse({"error": "Invalid time format."}, status=400)

    tz = ZoneInfo("Europe/Athens")
    start_dt = datetime.combine(start_date_obj, start_time_obj, tzinfo=tz)
    end_dt = datetime.combine(end_date_obj, end_time_obj, tzinfo=tz)

    if end_dt < start_dt:
        return JsonResponse({"error": "End date cannot be earlier than start date."}, status=400)

    sci_field = ScientificField.objects.filter(id=scientific_field_id).first()
    if not sci_field:
        return JsonResponse({"error": "Scientific field not found."}, status=404)

    now = timezone.now().astimezone(tz)
    def compute_state(start_date, end_date, start_time, end_time):
        if not start_date or not end_date:
            return "pending"
        start_t = start_time or dt_time(0, 0)
        end_t = end_time or dt_time(23, 59)
        start_dt_local = datetime.combine(start_date, start_t, tzinfo=tz)
        end_dt_local = datetime.combine(end_date, end_t, tzinfo=tz)
        if now < start_dt_local:
            return "pending"
        if now > end_dt_local:
            return "completed"
        return "active"

    if position_id:
        position = Position.objects.filter(id=position_id).first()
        if not position:
            return JsonResponse({"error": "Position not found."}, status=404)

        if position.scientific_field_id != sci_field.id:
            existing_position = getattr(sci_field, "position", None)
            if existing_position and existing_position.id != position.id:
                return JsonResponse({"error": "Position already exists for this scientific field."}, status=409)
            position.scientific_field = sci_field

        position.start_date = start_date_obj
        position.end_date = end_date_obj
        position.start_time = start_time_obj
        position.end_time = end_time_obj
        position.save(update_fields=["scientific_field", "start_date", "end_date", "start_time", "end_time"])

        return JsonResponse(
            {
                "message": "Position updated successfully.",
                "positionId": position.id,
                "scientificFieldId": sci_field.id,
                "state": compute_state(
                    position.start_date,
                    position.end_date,
                    position.start_time,
                    position.end_time,
                ),
            },
            status=200,
        )

    existing_position = getattr(sci_field, "position", None)
    if existing_position:
        return JsonResponse({"error": "Position already exists for this scientific field."}, status=409)

    position = Position.objects.create(
        scientific_field=sci_field,
        start_date=start_date_obj,
        end_date=end_date_obj,
        start_time=start_time_obj,
        end_time=end_time_obj,
    )

    return JsonResponse(
        {
            "message": "Position created successfully.",
            "positionId": position.id,
            "scientificFieldId": sci_field.id,
            "state": compute_state(
                position.start_date,
                position.end_date,
                position.start_time,
                position.end_time,
            ),
        },
        status=201,
    )


@api_view(["DELETE"])
def position_detail(request, position_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)

    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user or user.role != "admin":
        return JsonResponse({"error": "Only admins can delete positions."}, status=403)

    position = Position.objects.select_related("scientific_field").filter(id=position_id).first()
    if not position:
        return JsonResponse({"error": "Position not found."}, status=404)

    tz = ZoneInfo("Europe/Athens")
    now = timezone.now().astimezone(tz)

    def compute_state(start_date, end_date, start_time, end_time):
        if not start_date or not end_date:
            return "pending"
        start_t = start_time or dt_time(0, 0)
        end_t = end_time or dt_time(23, 59)
        start_dt = datetime.combine(start_date, start_t, tzinfo=tz)
        end_dt = datetime.combine(end_date, end_t, tzinfo=tz)
        if now < start_dt:
            return "pending"
        if now > end_dt:
            return "completed"
        return "active"

    state = compute_state(
        position.start_date,
        position.end_date,
        position.start_time,
        position.end_time,
    )
    if state in {"active", "completed"}:
        return JsonResponse(
            {"error": "Cannot delete an active or completed position."},
            status=409,
        )

    position.delete()
    return JsonResponse({"message": "Position deleted successfully."}, status=200)


@csrf_exempt
@api_view(["POST"])
def change_password(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token missing."}, status=401)
    token = auth_header.split(" ")[1]

    payload = decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Invalid or expired token."}, status=401)

    user_id = payload.get("user_id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    current_password = request.data.get("currentPassword", "")
    new_password = request.data.get("newPassword", "")

    if not current_password or not new_password:
        return JsonResponse({"error": "Όλα τα πεδία είναι υποχρεωτικά."}, status=400)

    if not user.check_password(current_password):
        return JsonResponse({"error": "Ο τρέχων κωδικός πρόσβασης είναι λανθασμένος."}, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return JsonResponse({"message": "Ο κωδικός πρόσβασης άλλαξε επιτυχώς."}, status=200)