from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0033_remove_userprofile_papers"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhdDegree",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("acquired_at", models.DateField()),
                ("is_foreign_institute", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "doatap_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="phd_doatap_documents",
                        to="app.vaultdocument",
                    ),
                ),
                (
                    "vault_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="phd_degree_documents",
                        to="app.vaultdocument",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phd_degrees",
                        to="app.user",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="application",
            name="phd_degree",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="applications",
                to="app.phddegree",
            ),
        ),
    ]
