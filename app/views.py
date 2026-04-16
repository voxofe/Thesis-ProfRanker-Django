from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ApplicationSerializer
from concurrent.futures import ThreadPoolExecutor
from .services.sjr import get_sjr_quartile
from .utils.calculate import calculate_points
from .models import Application, Paper, User, Position, ScientificField, Course, UserProfile, EmploymentCertificate, BioSupportingDocument
from .utils.jwt_utils import generate_jwt, decode_jwt
from django.views.decorators.csrf import csrf_exempt
import time
import json
from datetime import datetime, time as dt_time
from django.utils import timezone
from zoneinfo import ZoneInfo
from app.constants.departments import get_school_of_department
import os

# Register
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
    user_data = {
        "id": user.id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "mobileNumber": user.mobile_number,
        "landlineNumber": user.landline_number,
        "streetAddress": user.street_address,
        "city": user.city,
        "postalCode": user.postal_code,
        "role": user.role,
        "gender": user.gender,
    }
    user_data["applications"] = []

    def get_filename(filefield):
        if filefield and filefield.name:
            return filefield.name.split('/')[-1]
        return None

    def build_application_form(app):
        return {
            "id": app.id,
            "positionId": app.position.id if app.position else None,
            "phoneNumber": app.phone_number,
            "landlineNumber": app.landline_number,
            "streetAddress": app.street_address,
            "city": app.city,
            "postalCode": app.postal_code,
            "isPublicEmployee": app.is_public_employee,
            "phdTitle": app.phd_title,
            "phdAcquisitionDate": app.phd_acquisition_date,
            "phdIsFromForeignInstitute": app.phd_is_from_foreign_institute,
            "scientificField": app.position.scientific_field.name if app.position else None,
            "workExperience": app.work_experience,
            "hasNotParticipatedInPastProgram": app.has_not_participated_in_past_program,
            "isEuCitizenNonGreek": app.is_eu_citizen_non_greek,
            "cvDocument": get_filename(app.cv_document),
            "bioSupportingDocuments": [
                {
                    "id": doc.id,
                    "name": get_filename(doc.file),
                }
                for doc in app.bio_supporting_documents.all()
            ],
            "phdDocument": get_filename(app.phd_document),
            "doatapDocument": get_filename(app.doatap_document),
            "coursePlanDocument": get_filename(app.course_plan_document),
            "militaryObligationsDocument": get_filename(app.military_obligations_document),
            "employmentCertificates": [
                {
                    "id": cert.id,
                    "name": get_filename(cert.file),
                }
                for cert in app.employment_certificates.all()
            ],
            "publicEmployeePermissionDocument": get_filename(app.public_employee_permission_document),
            "notParticipatedDeclarationDocument": get_filename(app.not_participated_declaration_document),
            "euCitizenGreekLanguageCertificateDocument": get_filename(app.eu_citizen_greek_language_certificate_document),
            "responsibleDeclarationDocument": get_filename(app.responsible_declaration_document),
            "papers": [
                {
                    "id": paper.id,
                    "type": paper.type,
                    "paperTitle": paper.paper_title,
                    "journalConfTitle": paper.journal_conf_title,
                    "year": paper.year,
                    "issn": paper.issn,
                    "country": paper.country,
                    "quartile": paper.quartile
                }
                for paper in app.papers.all()
            ],
            "positionEndDate": app.position.end_date if app.position else None,
            "positionStartDate": app.position.start_date if app.position else None,
        }

    applications = list(
        user.applications.select_related("position", "position__scientific_field")
        .prefetch_related("bio_supporting_documents", "employment_certificates", "papers")
        .order_by("-submitted_at", "-id")
    )
    if applications:
        forms = [build_application_form(app) for app in applications]
        user_data["applications"] = forms
        user_data["form"] = forms[0]

    return JsonResponse(user_data, safe=False)


def build_profile_response(user, profile, applications=None):
    tz = ZoneInfo("Europe/Athens")

    def file_info(file_field, key):
        if not file_field:
            return {"name": None, "downloadPath": None}
        return {
            "name": file_field.name.split("/")[-1],
            "downloadPath": f"/api/profile/documents/{key}",
        }

    preferred_sf = profile.preferred_scientific_field
    if not preferred_sf and applications:
        first_app = applications[0]
        if first_app.position:
            preferred_sf = first_app.position.scientific_field

    applications_data = []
    for application in applications or []:
        sf = application.position.scientific_field if application.position else None
        submit_date = (
            timezone.localtime(application.submitted_at, tz).strftime("%d-%m-%Y %H:%M")
            if application.submitted_at
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
                "totalPoints": application.total_points,
            }
        )

    return {
        "user": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "mobileNumber": user.mobile_number,
            "landlineNumber": user.landline_number,
            "streetAddress": user.street_address,
            "city": user.city,
            "postalCode": user.postal_code,
            "role": user.role,
            "gender": user.gender,
        },
        "preferredScientificFieldId": preferred_sf.id if preferred_sf else None,
        "preferredScientificFieldLabel": preferred_sf.name if preferred_sf else "",
        "documents": {
            "cv": file_info(profile.cv_document, "cv"),
            "phd": file_info(profile.phd_document, "phd"),
            "doatap": file_info(profile.doatap_document, "doatap"),
            "coursePlan": file_info(profile.course_plan_document, "coursePlan"),
            "military": file_info(profile.military_obligations_document, "military"),    
        },
        "applications": applications_data,
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
        .order_by("-submitted_at", "-id")
    )

    if request.method == "PUT":
        data = request.data
        first_name = data.get("firstName")
        last_name = data.get("lastName")
        email = data.get("email")
        mobile_number = data.get("mobileNumber")
        landline_number = data.get("landlineNumber")
        street_address = data.get("streetAddress")
        city = data.get("city")
        postal_code = data.get("postalCode")
        gender = data.get("gender")
        preferred_sf_id = data.get("preferredScientificFieldId")

        if email and email != user.email and User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already registered."}, status=400)

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            user.email = email
        if mobile_number is not None:
            user.mobile_number = mobile_number
        if landline_number is not None:
            user.landline_number = landline_number
        if street_address is not None:
            user.street_address = street_address
        if city is not None:
            user.city = city
        if postal_code is not None:
            user.postal_code = postal_code
        if gender in {"male", "female", None, ""}:
            user.gender = gender or None
        user.save()

        if preferred_sf_id in [None, "", "null"]:
            profile.preferred_scientific_field = None
        else:
            sf = ScientificField.objects.filter(id=preferred_sf_id).first()
            if not sf:
                return JsonResponse({"error": "Scientific field not found."}, status=404)
            profile.preferred_scientific_field = sf
        profile.save()

    response = build_profile_response(user, profile, applications)
    return JsonResponse(response, safe=False)


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

    field_map = {
        "cvDocument": "cv_document",
        "phdDocument": "phd_document",
        "doatapDocument": "doatap_document",
        "coursePlanDocument": "course_plan_document",
        "militaryObligationsDocument": "military_obligations_document",
    }

    for incoming, model_field in field_map.items():
        new_file = request.FILES.get(incoming)
        if new_file:
            old_file = getattr(profile, model_field)
            if old_file:
                old_file.delete(save=False)
            setattr(profile, model_field, new_file)

    profile.save()
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

    document_map = {
        "cv": profile.cv_document,
        "phd": profile.phd_document,
        "doatap": profile.doatap_document,
        "coursePlan": profile.course_plan_document,
        "military": profile.military_obligations_document,
    }

    file_field = document_map.get(doc_key)
    if not file_field or not file_field.name:
        return JsonResponse({"error": "Document not found."}, status=404)

    filename = os.path.basename(file_field.name)
    response = FileResponse(file_field.open("rb"), as_attachment=True, filename=filename)
    response["Content-Type"] = "application/octet-stream"
    return response

# Handle Form Submission
def process_paper(paper):
    if paper.get("type") == "journal":
        return get_sjr_quartile(paper.get("year"), paper.get("issn"))
    return None

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
            papers_json = form_data.get("papers", "[]")
            papers = json.loads(papers_json)

            # --- Require position for unique application ---
            position_id = form_data.get("positionId")
            if not position_id or str(position_id).lower() in {"", "null", "none"}:
                return JsonResponse({"error": "Position is required."}, status=400)

            try:
                position = Position.objects.get(id=position_id)
            except Position.DoesNotExist:
                return JsonResponse({"error": "Position not found."}, status=404)

            # --- Get or create Application ---
            application, created = Application.objects.get_or_create(
                user=user,
                position=position,
            )

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

            application.position = position

            application.work_experience = int(form_data.get("workExperience", 0))
            application.has_not_participated_in_past_program = form_data.get("hasNotParticipatedInPastProgram") == "true"
            application.is_eu_citizen_non_greek = form_data.get("isEuCitizenNonGreek") == "true"

            # --- Handle file fields (replace if new file uploaded) ---
            def handle_file(field_name, new_file):
                old_file = getattr(application, field_name)
                if new_file:
                    # Always delete the old file if it exists, even if the name is the same
                    if old_file:
                        old_file.delete(save=False)
                    setattr(application, field_name, new_file)
                # If no new file, keep the old one

            handle_file("cv_document", request.FILES.get("cvDocument"))
            handle_file("phd_document", request.FILES.get("phdDocument"))
            handle_file("doatap_document", request.FILES.get("doatapDocument"))
            handle_file("course_plan_document", request.FILES.get("coursePlanDocument"))
            handle_file("military_obligations_document", request.FILES.get("militaryObligationsDocument"))
            handle_file("public_employee_permission_document", request.FILES.get("publicEmployeePermissionDocument"))
            handle_file("not_participated_declaration_document", request.FILES.get("notParticipatedDeclarationDocument"))
            handle_file("eu_citizen_greek_language_certificate_document", request.FILES.get("euCitizenGreekLanguageCertificateDocument"))
            handle_file("responsible_declaration_document", request.FILES.get("responsibleDeclarationDocument"))

            application.save()

            bio_supporting_document_files = request.FILES.getlist("bioSupportingDocuments")
            if bio_supporting_document_files:
                for doc in application.bio_supporting_documents.all():
                    if doc.file:
                        doc.file.delete(save=False)
                    doc.delete()

                for doc_file in bio_supporting_document_files:
                    if doc_file:
                        BioSupportingDocument.objects.create(
                            application=application,
                            file=doc_file,
                        )

            employment_certificate_files = request.FILES.getlist("employmentCertificateDocuments")
            should_replace_employment_certificates = bool(employment_certificate_files)

            if should_replace_employment_certificates:
                for cert in application.employment_certificates.all():
                    if cert.file:
                        cert.file.delete(save=False)
                    cert.delete()

                for cert_file in employment_certificate_files:
                    if cert_file:
                        EmploymentCertificate.objects.create(
                            application=application,
                            file=cert_file,
                        )

            # --- Papers resubmission logic ---
            # Build a dict of existing papers for quick lookup
            existing_papers = {paper.id: paper for paper in application.papers.all()}
            submitted_ids = set()

            # SJR results and multithreading
            sjr_results = []
            with ThreadPoolExecutor(max_workers=4) as executor: 
                future_to_paper = {executor.submit(process_paper, paper): paper for paper in papers}

                for future in future_to_paper:
                    paper = future_to_paper[future]
                    sjr_data = future.result()

                    notFound = ""
                    sjr_results.append({
                        "journalTitle": sjr_data["title"] if sjr_data else paper.get("journalConfTitle", notFound),
                        # "year": sjr_data["year"] if sjr_data else paper.get("year", notFound),
                        "issn": (
                            paper.get("issn") if sjr_data
                            else (
                                notFound if not paper.get("issn") or paper.get("issn") == notFound
                                else (
                                    paper.get("issn") if "Wrong" in paper.get("issn")
                                    else paper.get("issn") + " (Wrong)"
                                )
                            )
                        ),
                        "country": sjr_data["country"] if sjr_data else notFound,
                        "sjr_quartile": sjr_data["sjr_quartile"] if sjr_data else notFound,
                    })

                    sjr_result = sjr_results[-1]

                    paper_id = paper.get("id")
                    if paper_id and paper_id in existing_papers:
                        # Update existing paper
                        db_paper = existing_papers[paper_id]
                        db_paper.type = paper.get("type")
                        db_paper.paper_title = paper.get("paperTitle")
                        db_paper.journal_conf_title = sjr_result["journalTitle"]
                        db_paper.year = paper.get("year")
                        db_paper.issn = sjr_result["issn"]
                        db_paper.country = sjr_result["country"]
                        db_paper.quartile = sjr_result["sjr_quartile"]

                        db_paper.save()
                        submitted_ids.add(paper_id)
                    else:
                        # Create new paper
                        new_paper = Paper.objects.create(
                            application=application,
                            type=paper.get("type"),
                            paper_title=paper.get("paperTitle"),
                            journal_conf_title=sjr_result["journalTitle"],
                            year=paper.get("year"),
                            issn=sjr_result["issn"],
                            country=sjr_result["country"],
                            quartile=sjr_result["sjr_quartile"],

                        )
                        submitted_ids.add(new_paper.id)

            # Delete papers not in submitted
            for paper_id, db_paper in existing_papers.items():
                if paper_id not in submitted_ids:
                    db_paper.delete()

            # Retrieve all Paper instances for the application
            papers_qs = Paper.objects.filter(application=application)

            # Now calculate points AFTER papers are processed
            calculated_points = calculate_points(application, papers_qs)
            
            # Update the Application instance with the calculated points
            Application.objects.filter(id=application.id).update(**calculated_points)

            # Serialize the application instance
            application_serializer = ApplicationSerializer(application)

            end_time = time.time()
            execution_time = end_time - start_time
            print(f"⏱️ Total execution time: {execution_time:.4f} seconds\n")

            return JsonResponse({
                'message': 'Success',
                # 'sjr_results': sjr_results,
                # 'application': application_serializer.data
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

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

    def file_info(file_field, key):
        if not file_field:
            return {"url": None, "name": None, "downloadPath": None}
        download_path = f"/api/applicant/{application.id}/documents/{key}"
        return {
            "url": request.build_absolute_uri(file_field.url),
            "name": file_field.name.split("/")[-1],
            "downloadPath": download_path,
        }

    data = {
        "id": user.id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "phdTitle": application.phd_title,
        "phdAcquisitionDate": application.phd_acquisition_date.strftime("%d-%m-%Y") if application.phd_acquisition_date else "",
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
        "paperPoints": application.paper_points,
        "workExperiencePoints": application.work_experience_points,
        "notPastProgramPoints": application.not_past_program_points,
        "totalPoints": application.total_points,
        "papers": [
            {
                "id": paper.id,
                "type": paper.type,
                "paperTitle": paper.paper_title,
                "journalConfTitle": paper.journal_conf_title,
                "year": paper.year,
                "issn": paper.issn,
                "country": paper.country,
                "quartile": paper.quartile,
            }
            for paper in application.papers.all()
        ],
        "submitDate": timezone.localtime(application.submitted_at, ZoneInfo("Europe/Athens")).strftime("%d-%m-%Y %H:%M") if application.submitted_at else "",
        "positionStartDate": application.position.start_date.strftime("%d-%m-%Y") if application.position and application.position.start_date else "",
        "positionEndDate": application.position.end_date.strftime("%d-%m-%Y") if application.position and application.position.end_date else "",
        "positionStartTime": application.position.start_time.strftime("%H:%M") if application.position and application.position.start_time else "",
        "positionEndTime": application.position.end_time.strftime("%H:%M") if application.position and application.position.end_time else "",
        "documents": {
            "cv": file_info(application.cv_document, "cv"),
            "bioSupportingDocuments": [
                {
                    "id": doc.id,
                    "url": request.build_absolute_uri(doc.file.url),
                    "name": doc.file.name.split("/")[-1] if doc.file else None,
                    "downloadPath": None,
                }
                for doc in application.bio_supporting_documents.all()
                if doc.file
            ],
            "phd": file_info(application.phd_document, "phd"),
            "doatap": file_info(application.doatap_document, "doatap"),
            "coursePlan": file_info(application.course_plan_document, "coursePlan"),
            "military": file_info(application.military_obligations_document, "military"),
            "employmentCertificates": [
                {
                    "id": cert.id,
                    "url": request.build_absolute_uri(cert.file.url),
                    "name": cert.file.name.split("/")[-1] if cert.file else None,
                    "downloadPath": f"/api/applicant/{application.id}/employment-certificates/{cert.id}",
                }
                for cert in application.employment_certificates.all()
                if cert.file
            ],
            "publicEmployeePermission": file_info(application.public_employee_permission_document, "publicEmployeePermission"),
            "notParticipatedDeclaration": file_info(application.not_participated_declaration_document, "notParticipatedDeclaration"),
            "euCitizenGreekLanguageCertificate": file_info(application.eu_citizen_greek_language_certificate_document, "euCitizenGreekLanguageCertificate"),
            "responsibleDeclaration": file_info(application.responsible_declaration_document, "responsibleDeclaration"),
        },
    }
    return JsonResponse(data, safe=False)


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
    document_map = {
        "cv": application.cv_document,
        "phd": application.phd_document,
        "doatap": application.doatap_document,
        "coursePlan": application.course_plan_document,
        "military": application.military_obligations_document,
        "employmentCertificate": (
            application.employment_certificates.first().file
            if application.employment_certificates.exists()
            else None
        ),
        "publicEmployeePermission": application.public_employee_permission_document,
        "notParticipatedDeclaration": application.not_participated_declaration_document,
        "euCitizenGreekLanguageCertificate": application.eu_citizen_greek_language_certificate_document,
        "responsibleDeclaration": application.responsible_declaration_document,
    }

    file_field = document_map.get(doc_key)
    if not file_field:
        return JsonResponse({"error": "Document not found."}, status=404)
    if not file_field.name:
        return JsonResponse({"error": "Document not available."}, status=404)

    filename = os.path.basename(file_field.name)
    response = FileResponse(file_field.open("rb"), as_attachment=True, filename=filename)
    response["Content-Type"] = "application/octet-stream"
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
        sfs = ScientificField.objects.all()
        available_for_position = request.query_params.get("availableForPosition")
        if available_for_position and str(available_for_position).lower() in {"1", "true", "yes"}:
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

            sfs = [sf for sf in sfs if is_available(sf)]
        data = [
            {
                "id": sf.id,
                "name": sf.name,
                "department": sf.department,
                "school": sf.school,
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
                ]
            }
            for sf in sfs
        ]
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

    return JsonResponse(
        {
            "message": "Scientific field created successfully.",
            "scientificFieldId": sci_field.id,
        },
        status=201,
    )

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