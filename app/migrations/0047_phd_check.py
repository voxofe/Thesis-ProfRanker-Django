from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0046_rename_phddocument_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhdCheck",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("extracted_raw_text", models.TextField(blank=True, null=True)),
                ("extraction_status", models.CharField(choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")], default="pending", max_length=20)),
                ("extraction_error", models.TextField(blank=True, null=True)),
                ("page_count", models.PositiveIntegerField(blank=True, null=True)),
                ("extracted_text_length", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("phd_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="phd_checks", to="app.phddocument")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="phd_checks", to="app.user")),
                ("vault_document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="phd_checks", to="app.vaultdocument")),
            ],
        ),
    ]
