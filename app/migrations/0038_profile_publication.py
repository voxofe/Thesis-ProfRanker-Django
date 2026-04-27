from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0037_remove_publication_peer_reviewed"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfilePublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(blank=True, max_length=100, null=True)),
                ("publication_title", models.CharField(blank=True, max_length=255, null=True)),
                ("journal_conf_title", models.CharField(blank=True, max_length=255, null=True)),
                ("year", models.CharField(blank=True, max_length=4, null=True)),
                ("issn", models.CharField(blank=True, max_length=50, null=True)),
                ("country", models.CharField(blank=True, max_length=100, null=True)),
                ("quartile", models.CharField(blank=True, max_length=10, null=True)),
                ("authors", models.JSONField(blank=True, default=list, null=True)),
                ("publisher", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_publications",
                        to="app.user",
                    ),
                ),
            ],
        ),
    ]
