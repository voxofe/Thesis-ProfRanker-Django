from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0046_rename_phddocument_title"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="phd_title",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="phd_acquisition_date",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="phd_is_from_foreign_institute",
        ),
    ]
