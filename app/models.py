from django.db import models

class Application(models.Model):
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField( blank=True, null=True)
    scientific_field = models.CharField(max_length=255, blank=True, null=True)
    course_plan_document = models.FileField(upload_to='documents/', blank=True, null=True)
    phd_document = models.FileField(upload_to='documents/', blank=True, null=True)
    phd_acquisition_date = models.DateField( blank=True, null=True)
    phd_is_from_foreign_institute = models.BooleanField(default=False, blank=True, null=True)
    doatap_document = models.FileField(upload_to='documents/', blank=True, null=True)
    work_experience = models.IntegerField( blank=True, null=True)
    military_obligations_document = models.FileField(upload_to='documents/', blank=True, null=True)
    cv_document = models.FileField(upload_to='documents/', blank=True, null=True)
    has_not_participated_in_past_program = models.BooleanField(default=False, blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

class Paper(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="papers")  # 👈 One-to-Many Relationship
    type = models.CharField(max_length=100, blank=True, null=True)
    paper_title = models.CharField(max_length=255, blank=True, null=True)
    year = models.CharField(max_length=4, blank=True, null=True)
    journal_conf_title = models.CharField(max_length=255, blank=True, null=True)
    issn = models.CharField(max_length=50, blank=True, null=True)
    quartile = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.paper_title} ({self.year})"
