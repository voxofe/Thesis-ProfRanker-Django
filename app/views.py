from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ApplicationSerializer, PaperSerializer
from concurrent.futures import ThreadPoolExecutor
from .services.sjr import get_sjr_quartile
from .utils.calculate import calculate_points
from .models import Application, Paper, User
from .serializers import ApplicationSerializer, UserSerializer
from .utils.jwt_utils import generate_jwt, decode_jwt
from django.views.decorators.csrf import csrf_exempt
import time
import json
from datetime import datetime

# Register
@csrf_exempt
@api_view(["POST"])
def user_register(request):
    data = request.data
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password")

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already registered."}, status=400)

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role="guest"
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
        "role": user.role,
    }

    def get_filename(filefield):
        if filefield and filefield.name:
            return filefield.name.split('/')[-1]
        return None

    if hasattr(user, "application") and user.application:
        app = user.application
        user_data["form"] = {
            "id": app.id,
            "phdTitle": app.phd_title,
            "phdAcquisitionDate": app.phd_acquisition_date,
            "phdIsFromForeignInstitute": app.phd_is_from_foreign_institute,
            "scientificField": app.scientific_field,
            "workExperience": app.work_experience,
            "hasNotParticipatedInPastProgram": app.has_not_participated_in_past_program,

            "cvDocument": get_filename(app.cv_document),
            "phdDocument": get_filename(app.phd_document),
            "doatapDocument": get_filename(app.doatap_document),
            "coursePlanDocument": get_filename(app.course_plan_document),
            "militaryObligationsDocument": get_filename(app.military_obligations_document),
            
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
        }

    return JsonResponse(user_data, safe=False)

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

            # --- Get or create Application ---
            application, created = Application.objects.get_or_create(user=user)

            # --- Update simple fields ---

            application.phd_title = form_data.get("phdTitle")
            application.phd_acquisition_date = form_data.get("phdAcquisitionDate")
            application.phd_is_from_foreign_institute = form_data.get("phdIsFromForeignInstitute") == "true"
            application.scientific_field = form_data.get("scientificField")
            application.work_experience = int(form_data.get("workExperience", 0))
            application.has_not_participated_in_past_program = form_data.get("hasNotParticipatedInPastProgram") == "true"

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
            

            application.save()

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
def get_applicant_score(request, id):
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
        return JsonResponse({"error": "User not found."}, status=404)

    # Only allow if admin or requesting their own data
    if requesting_user.role != "admin" and requesting_user.id != id:
        return JsonResponse({"error": "Forbidden."}, status=403)

    application = get_object_or_404(Application, user__id=id)
    user = application.user

    # Build applicantData structure
    data = {
        "id": user.id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "phdTitle": application.phd_title,
        "phdAcquisitionDate": application.phd_acquisition_date.strftime("%d-%m-%Y") if application.phd_acquisition_date else "",
        "scientificField": application.scientific_field,
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
    }
    return JsonResponse(data, safe=False)

# Get All Scores
@api_view(["GET"])
def get_all_scores(request):
    applicants = User.objects.filter(role="applicant")
    result = []
    for user in applicants:
        app = getattr(user, "application", None)
        if app:
            # Format submitDate as "day-month-year hh:mm"
            if hasattr(app, "submitted_at") and app.submitted_at:
                submit_date = app.submitted_at.strftime("%d-%m-%Y %H:%M")
            else:
                submit_date = ""
            result.append({
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "scientificField": app.scientific_field,
                "submitDate": submit_date,
                "totalPoints": app.total_points,
            })
    return JsonResponse(result, safe=False)