from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    ROLES = [
        ('admin', 'Admin'),
        ('applicant', 'Applicant'),
        ('guest', 'Guest'),
    ]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLES)
    password = models.CharField(max_length=128)  # Store hashed password

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email} ({self.role})"

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

    def __str__(self):
        return f"{self.scientific_field.name} ({self.start_date} - {self.end_date})"

class Application(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="application", null=True, blank=True)
    phd_title = models.CharField(max_length=255, blank=True, null=True)
    phd_acquisition_date = models.DateField(blank=True, null=True)
    phd_is_from_foreign_institute = models.BooleanField(default=False, blank=True, null=True)
    work_experience = models.IntegerField(blank=True, null=True)
    has_not_participated_in_past_program = models.BooleanField(default=False, blank=True, null=True)

    cv_document = models.FileField(upload_to='documents/', blank=True, null=True, max_length=255)
    phd_document = models.FileField(upload_to='documents/', blank=True, null=True, max_length=255)
    doatap_document = models.FileField(upload_to='documents/', blank=True, null=True, max_length=255)
    course_plan_document = models.FileField(upload_to='documents/', blank=True, null=True, max_length=255)
    military_obligations_document = models.FileField(upload_to='documents/', blank=True, null=True, max_length=255)

    course_plan_relevance_points = models.IntegerField(default=0, blank=True, null=True)
    course_material_structure_points = models.IntegerField(default=0, blank=True, null=True)
    thesis_relevance_points = models.IntegerField(default=0, blank=True, null=True)
    paper_points = models.IntegerField(default=0, blank=True, null=True)
    work_experience_points = models.IntegerField(default=0, blank=True, null=True)
    not_past_program_points = models.IntegerField(default=0, blank=True, null=True)
    total_points = models.IntegerField(default=0, blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="applications", null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.user.email}"

class Paper(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="papers")  # One-to-Many Relationship
    type = models.CharField(max_length=100, blank=True, null=True)
    paper_title = models.CharField(max_length=255, blank=True, null=True)
    journal_conf_title = models.CharField(max_length=255, blank=True, null=True)
    year = models.CharField(max_length=4, blank=True, null=True)
    issn = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    quartile = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.paper_title} ({self.year})"

