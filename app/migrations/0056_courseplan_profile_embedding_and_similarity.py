from django.db import migrations, models
import django.db.models.deletion
import pgvector.django.vector


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0055_courseplan"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="course_plan_cosine_similarity",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="CoursePlanProfile",
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
                ("profile_text", models.TextField(blank=True, null=True)),
                (
                    "original_language",
                    models.CharField(
                        blank=True,
                        choices=[("gr", "Greek"), ("en", "English")],
                        max_length=2,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "application",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_plan_profile",
                        to="app.application",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CoursePlanEmbedding",
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
                ("model_name", models.CharField(max_length=255)),
                (
                    "language",
                    models.CharField(
                        choices=[("gr", "Greek"), ("en", "English")],
                        default="gr",
                        max_length=2,
                    ),
                ),
                ("vector", pgvector.django.vector.VectorField(dimensions=1536)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embeddings",
                        to="app.courseplanprofile",
                    ),
                ),
            ],
        ),
    ]
