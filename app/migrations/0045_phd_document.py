from django.db import migrations, models
import django.db.models.deletion
import app.models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0044_scientificfieldembedding_language"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhdDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("thesis_title", models.CharField(max_length=500)),
                ("pdf_file", models.FileField(max_length=255, upload_to=app.models.phd_document_upload_path)),
                ("original_filename", models.CharField(max_length=255)),
                ("extracted_raw_text", models.TextField(blank=True, null=True)),
                ("extraction_status", models.CharField(choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")], default="pending", max_length=20)),
                ("extraction_error", models.TextField(blank=True, null=True)),
                ("page_count", models.PositiveIntegerField(blank=True, null=True)),
                ("extracted_text_length", models.PositiveIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "application",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="phd_documents", to="app.application"),
                ),
            ],
        ),
    ]
