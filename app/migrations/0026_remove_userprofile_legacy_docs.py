from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0025_move_contact_fields_to_userprofile"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="cv_document",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="phd_document",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="doatap_document",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="course_plan_document",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="military_obligations_document",
        ),
    ]
