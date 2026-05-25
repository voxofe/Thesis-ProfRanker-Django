from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0045_phd_document"),
    ]

    operations = [
        migrations.RenameField(
            model_name="phddocument",
            old_name="thesis_title",
            new_name="title",
        ),
    ]
