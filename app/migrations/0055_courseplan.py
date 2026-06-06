from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0054_application_phd_cosine_similarity"),
    ]

    operations = [
        migrations.CreateModel(
            name="CoursePlan",
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
                ("general_description", models.TextField()),
                ("learning_objectives", models.TextField()),
                ("course_schedule", models.TextField()),
                ("delivery_methods", models.TextField()),
                ("bibliography_material", models.TextField()),
                ("learning_outcomes", models.TextField()),
                ("assessment_methods_criteria", models.TextField()),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_plans",
                        to="app.application",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_plans",
                        to="app.course",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="courseplan",
            constraint=models.UniqueConstraint(
                fields=("application", "course"),
                name="unique_course_plan_per_application_course",
            ),
        ),
    ]
