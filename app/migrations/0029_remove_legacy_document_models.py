from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0028_rename_profiledocument_to_vaultdocument"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BioSupportingDocument",
        ),
        migrations.DeleteModel(
            name="EmploymentCertificate",
        ),
    ]
