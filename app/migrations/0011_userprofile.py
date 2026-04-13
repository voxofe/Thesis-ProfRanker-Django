from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0010_user_gender"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "cv_document",
                    models.FileField(blank=True, max_length=255, null=True, upload_to="profile_documents/"),
                ),
                (
                    "phd_document",
                    models.FileField(blank=True, max_length=255, null=True, upload_to="profile_documents/"),
                ),
                (
                    "doatap_document",
                    models.FileField(blank=True, max_length=255, null=True, upload_to="profile_documents/"),
                ),
                (
                    "course_plan_document",
                    models.FileField(blank=True, max_length=255, null=True, upload_to="profile_documents/"),
                ),
                (
                    "military_obligations_document",
                    models.FileField(blank=True, max_length=255, null=True, upload_to="profile_documents/"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "preferred_scientific_field",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="preferred_by_users",
                        to="app.scientificfield",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="app.user",
                    ),
                ),
            ],
        ),
    ]
