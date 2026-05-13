"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings 
from django.conf.urls.static import static 
from django.contrib import admin
from django.urls import path, re_path
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/register', views.user_register, name='user_register'),
    path('api/user/register-admin', views.user_register_admin, name='user_register_admin'),
    path('api/user/login', views.user_login, name='user_login'),
    path('api/email/test', views.email_test, name='email_test'),
    path('api/jobs/positions/close-emails', views.cron_send_position_closed_emails, name='cron_send_position_closed_emails'),
    path('api/users/getByToken', views.get_user_by_token, name='get_user_by_token'),
    path('api/profile', views.profile_detail, name='profile_detail'),
    path('api/profile/documents', views.profile_documents_upload, name='profile_documents_upload'),
    path('api/profile/documents/<str:doc_key>', views.profile_document_download, name='profile_document_download'),
    path('api/profile/vault/<int:doc_id>', views.profile_document_manage, name='profile_document_manage'),
    path('api/profile/vault', views.profile_document_create, name='profile_document_create'),
    path('api/submit', views.handle_form_submission, name='handle_form_submission'),
    path('api/applications/<int:application_id>', views.get_application_detail, name='get_application_detail'),
    path('api/applications/<int:application_id>/delete', views.delete_application, name='delete_application'),
    path('api/applicant/<int:application_id>', views.get_applicant_score, name='get_applicant_score'),
    path('api/applicant/<int:application_id>/documents/<str:doc_key>', views.download_applicant_document, name='download_applicant_document'),
    path('api/applicant/all', views.get_all_scores, name='get_all_scores'),
    path('api/scientific-fields', views.scientific_fields_collection, name='scientific_fields_collection'),
    path('api/positions', views.positions_collection, name='positions_collection')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
