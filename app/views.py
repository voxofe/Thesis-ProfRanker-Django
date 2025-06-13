from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ApplicationSerializer, PaperSerializer
from concurrent.futures import ThreadPoolExecutor
from .services.sjr import get_sjr_quartile
from .utils import calculate_points
from .models import Application, Paper
from .serializers import ApplicationSerializer
import time
import json


def process_paper(paper):
    if paper.get("type") == "journal":
        return get_sjr_quartile(paper.get("year"), paper.get("issn"))
    return None

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])  # Handle both form data and file uploads
def handle_form_submission(request):
    if request.method == 'POST':
        start_time = time.time()
        try:

            form_data = request.data
            papers_json = form_data.get("papers", "[]")
            papers = json.loads(papers_json)

            # Create the Application instance WITHOUT points first
            application = Application.objects.create(
                first_name=form_data.get("firstName"),
                last_name=form_data.get("lastName"),
                email=form_data.get("email"),
                scientific_field=form_data.get("scientificField"),
                phd_acquisition_date=form_data.get("phdAcquisitionDate"),
                phd_is_from_foreign_institute=form_data.get("phdIsFromForeignInstitute") == "true",
                work_experience=int(form_data.get("workExperience", 0)),
                has_not_participated_in_past_program=form_data.get("hasNotParticipatedInPastProgram") == "true",
                
                # Handling file uploads
                course_plan_document=request.FILES.get("coursePlanDocument"),
                phd_document=request.FILES.get("phdDocument"),
                doatap_document=request.FILES.get("doatapDocument"),
                military_obligations_document=request.FILES.get("militaryObligationsDocument"),
                cv_document=request.FILES.get("cvDocument"),

            )

            # Process papers FIRST
            sjr_results = []
            with ThreadPoolExecutor(max_workers=4) as executor: 
                future_to_paper = {executor.submit(process_paper, paper): paper for paper in papers}

                for future in future_to_paper:
                    paper = future_to_paper[future]
                    sjr_data = future.result()

                    notFound = "N/A"
                    sjr_results.append({
                        "journalTitle": sjr_data["title"] if sjr_data else notFound,
                        "country": sjr_data["country"] if sjr_data  else notFound,
                        "sjr_quartile": sjr_data["sjr_quartile"] if sjr_data  else notFound,
                        "issn": paper.get("issn") if sjr_data  else paper.get("issn") + " (Wrong)"
                    })

                    sjr_result = sjr_results[-1]

                    Paper.objects.create(
                        application=application,
                        type=paper.get("type"),
                        paper_title=paper.get("paperTitle"),
                        year=paper.get("year"),
                        journal_conf_title= sjr_result["journalTitle"],
                        issn=sjr_result["issn"],
                        quartile=sjr_result["sjr_quartile"],
                        country=sjr_result["country"],
                    )
            # Retrieve all Paper instances for the application
            papers = Paper.objects.filter(application=application)

            # Now calculate points AFTER papers are processed
            calculated_points = calculate_points(application, papers)
            
            # Update the Application instance with the calculated points
            Application.objects.filter(id=application.id).update(**calculated_points)

            # Serialize the application instance
            application_serializer = ApplicationSerializer(application)

            end_time = time.time()
            execution_time = end_time - start_time
            print(f"⏱️ Total execution time: {execution_time:.4f} seconds\n")

            return JsonResponse({
                'message': 'Success',
                'sjr_results': sjr_results,
                'application': application_serializer.data
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@api_view(["GET"])
def get_applicant(request, id):
    applicant = get_object_or_404(Application, id=id)
    serializer = ApplicationSerializer(applicant)
    return JsonResponse(serializer.data, safe=False)

@api_view(["GET"])
def get_applicant_papers(request, id):
    """
    Fetch all papers associated with a specific applicant ID.
    """
    application = get_object_or_404(Application, id=id)
    papers = application.papers.all()  # Use the related_name "papers" from the Paper model
    serializer = PaperSerializer(papers, many=True)
    return JsonResponse(serializer.data, safe=False)
