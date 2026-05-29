from django.db import migrations, models
import pgvector.django


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0049_phd_abstract_keywords_remove_checks"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhdProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("abstract", models.TextField(blank=True, null=True)),
                ("keywords", models.JSONField(blank=True, default=list, null=True)),
                ("profile_text", models.TextField(blank=True, null=True)),
                ("title_en", models.CharField(blank=True, max_length=255, null=True)),
                ("abstract_en", models.TextField(blank=True, null=True)),
                ("keywords_en", models.JSONField(blank=True, default=list, null=True)),
                ("profile_text_en", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "phd_degree",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="profile", to="app.phddegree"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PhdEmbedding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_name", models.CharField(max_length=255)),
                ("language", models.CharField(choices=[("gr", "Greek"), ("en", "English")], default="gr", max_length=2)),
                ("vector", pgvector.django.VectorField(dimensions=1536)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "phd_degree",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="embeddings", to="app.phddegree"),
                ),
            ],
        ),
    ]
