from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0026_remove_userprofile_legacy_docs"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="preferred_scientific_field",
        ),
    ]
