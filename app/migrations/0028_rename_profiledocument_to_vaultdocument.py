from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0027_remove_userprofile_preferred_scientific_field"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ProfileDocument",
            new_name="VaultDocument",
        ),
        migrations.RenameField(
            model_name="applicationdocument",
            old_name="profile_document",
            new_name="vault_document",
        ),
        migrations.AddField(
            model_name="vaultdocument",
            name="source_application",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vault_documents",
                to="app.application",
            ),
        ),
    ]
