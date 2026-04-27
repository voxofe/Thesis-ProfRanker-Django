from django.db import models
from datetime import time as dt_time
from django.contrib.auth.hashers import make_password, check_password


def vault_document_upload_path(instance, filename):
    user_id = instance.user_id or "unknown"
    application_id = getattr(instance, "application_id", None)
    if application_id:
        return f"documents/user_{user_id}/application_{application_id}/{filename}"
    return f"documents/user_{user_id}/vault/{filename}"

class User(models.Model):
    ROLES = [
        ('admin', 'Admin'),
        ('applicant', 'Applicant'),
        ('guest', 'Guest'),
    ]
    GENDERS = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLES)
    gender = models.CharField(max_length=6, choices=GENDERS, blank=True, null=True)
    password = models.CharField(max_length=128)  # Store hashed password

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email} ({self.role})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile_number = models.CharField(max_length=30, blank=True, null=True)
    landline_number = models.CharField(max_length=30, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_public_employee = models.BooleanField(default=False, blank=True, null=True)
    is_eu_citizen_non_greek = models.BooleanField(default=False, blank=True, null=True)
    has_not_participated_in_past_program = models.BooleanField(default=False, blank=True, null=True)
    phd_title = models.CharField(max_length=255, blank=True, null=True)
    phd_acquisition_date = models.DateField(blank=True, null=True)
    phd_is_from_foreign_institute = models.BooleanField(default=False, blank=True, null=True)
    work_experience = models.IntegerField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.first_name} {self.user.last_name}"


class ProfilePublication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile_publications")
    type = models.CharField(max_length=100, blank=True, null=True)
    publication_title = models.CharField(max_length=255, blank=True, null=True)
    journal_conf_title = models.CharField(max_length=255, blank=True, null=True)
    year = models.CharField(max_length=4, blank=True, null=True)
    issn = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    quartile = models.CharField(max_length=10, blank=True, null=True)
    authors = models.JSONField(default=list, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.publication_title} ({self.year})"


class VaultDocument(models.Model):
    DOCUMENT_TYPES = [
        ("cv", "CV"),
        ("phd", "PhD"),
        ("doatap", "DOATAP"),
        ("course_plan", "Course Plan"),
        ("military", "Military Obligations"),
        ("public_employee_permission", "Public Employee Permission"),
        ("not_participated_declaration", "Not Participated Declaration"),
        ("eu_citizen_greek_language_certificate", "EU Citizen Greek Language Certificate"),
        ("responsible_declaration", "Responsible Declaration"),
        ("bio_supporting", "Bio Supporting"),
        ("employment_certificate", "Employment Certificate"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vault_documents")
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to=vault_document_upload_path, max_length=255)
    is_default = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.doc_type} ({self.id})"


class PhdDegree(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phd_degrees")
    title = models.CharField(max_length=255)
    acquired_at = models.DateField()
    vault_document = models.ForeignKey(
        VaultDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phd_degree_documents",
    )
    is_foreign_institute = models.BooleanField(default=False)
    doatap_document = models.ForeignKey(
        VaultDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phd_doatap_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.title} ({self.acquired_at})"


class ApplicationDocument(models.Model):
    application = models.ForeignKey(
        "Application",
        on_delete=models.CASCADE,
        related_name="application_documents",
    )
    vault_document = models.ForeignKey(
        VaultDocument,
        on_delete=models.CASCADE,
        related_name="application_links",
    )
    doc_type = models.CharField(max_length=50, choices=VaultDocument.DOCUMENT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application {self.application_id} - {self.doc_type} ({self.vault_document_id})"

class ScientificField(models.Model):
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    school = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.department})"

class Course(models.Model):
    SEMESTERS = [
        ('fall', 'Χειμερινό'),
        ('spring', 'Εαρινό'),
    ]
    CATEGORIES = [
        ('mandatory', 'Υποχρεωτικό'),
        ('elective', 'Επιλογής'),
    ]
    code = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    semester = models.CharField(max_length=50, blank=True, null=True)
    teaching_units = models.IntegerField(blank=True, null=True)
    ects = models.FloatField(blank=True, null=True)
    theory_hours = models.IntegerField(blank=True, null=True)
    lab_hours = models.IntegerField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    scientific_field = models.ForeignKey(ScientificField, on_delete=models.CASCADE, related_name="courses")

    def __str__(self):
        return self.name

class Position(models.Model):
    scientific_field = models.OneToOneField(ScientificField, on_delete=models.CASCADE, related_name="position")
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(default=dt_time(0, 0))
    end_time = models.TimeField(default=dt_time(23, 59))

    def __str__(self):
        return f"{self.scientific_field.name} ({self.start_date} - {self.end_date})"

class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications", null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    landline_number = models.CharField(max_length=20, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_public_employee = models.BooleanField(default=False, blank=True, null=True)
    phd_title = models.CharField(max_length=255, blank=True, null=True)
    phd_acquisition_date = models.DateField(blank=True, null=True)
    phd_is_from_foreign_institute = models.BooleanField(default=False, blank=True, null=True)
    work_experience = models.IntegerField(blank=True, null=True)
    has_not_participated_in_past_program = models.BooleanField(default=False, blank=True, null=True)
    is_eu_citizen_non_greek = models.BooleanField(default=False, blank=True, null=True)

    phd_degree = models.ForeignKey(
        PhdDegree,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )

    course_plan_relevance_points = models.IntegerField(default=0, blank=True, null=True)
    course_material_structure_points = models.IntegerField(default=0, blank=True, null=True)
    thesis_relevance_points = models.IntegerField(default=0, blank=True, null=True)
    publication_points = models.IntegerField(default=0, blank=True, null=True)
    work_experience_points = models.IntegerField(default=0, blank=True, null=True)
    not_past_program_points = models.IntegerField(default=0, blank=True, null=True)
    total_points = models.IntegerField(default=0, blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="applications", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "position"],
                name="unique_application_per_user_position",
            )
        ]

    def __str__(self):
        if not self.user:
            return f"Application #{self.id}"
        return f"{self.user.first_name} {self.user.last_name} - {self.user.email}"

class Publication(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="publications")  # One-to-Many Relationship
    type = models.CharField(max_length=100, blank=True, null=True)
    publication_title = models.CharField(max_length=255, blank=True, null=True)
    journal_conf_title = models.CharField(max_length=255, blank=True, null=True)
    year = models.CharField(max_length=4, blank=True, null=True)
    issn = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    quartile = models.CharField(max_length=10, blank=True, null=True)
    authors = models.JSONField(default=list, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.publication_title} ({self.year})"

