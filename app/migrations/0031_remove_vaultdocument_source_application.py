from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0030_remove_application_file_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="vaultdocument",
            name="source_application",
        ),
    ]
