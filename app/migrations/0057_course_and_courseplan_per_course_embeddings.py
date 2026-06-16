from django.db import migrations, models
import django.db.models.deletion
import pgvector.django.vector


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0056_courseplan_profile_embedding_and_similarity"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseProfile",
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
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="app.course",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CourseEmbedding",
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
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embeddings",
                        to="app.course",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="CoursePlanEmbedding",
        ),
        migrations.DeleteModel(
            name="CoursePlanProfile",
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
                    "course_plan",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="app.courseplan",
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
