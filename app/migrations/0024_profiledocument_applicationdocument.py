from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0023_alter_application_user_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfileDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("cv", "CV"),
                            ("phd", "PhD"),
                            ("doatap", "DOATAP"),
                            ("course_plan", "Course Plan"),
                            ("military", "Military Obligations"),
                            ("public_employee_permission", "Public Employee Permission"),
                            ("not_participated_declaration", "Not Participated Declaration"),
                            (
                                "eu_citizen_greek_language_certificate",
                                "EU Citizen Greek Language Certificate",
                            ),
                            ("responsible_declaration", "Responsible Declaration"),
                            ("bio_supporting", "Bio Supporting"),
                            ("employment_certificate", "Employment Certificate"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "file",
                    models.FileField(max_length=255, upload_to="profile_documents/"),
                ),
                ("is_default", models.BooleanField(default=False)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_documents",
                        to="app.user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("cv", "CV"),
                            ("phd", "PhD"),
                            ("doatap", "DOATAP"),
                            ("course_plan", "Course Plan"),
                            ("military", "Military Obligations"),
                            ("public_employee_permission", "Public Employee Permission"),
                            ("not_participated_declaration", "Not Participated Declaration"),
                            (
                                "eu_citizen_greek_language_certificate",
                                "EU Citizen Greek Language Certificate",
                            ),
                            ("responsible_declaration", "Responsible Declaration"),
                            ("bio_supporting", "Bio Supporting"),
                            ("employment_certificate", "Employment Certificate"),
                        ],
                        max_length=50,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="application_documents",
                        to="app.application",
                    ),
                ),
                (
                    "profile_document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="application_links",
                        to="app.profiledocument",
                    ),
                ),
            ],
        ),
    ]
