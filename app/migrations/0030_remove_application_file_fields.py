from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0029_remove_legacy_document_models"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="application",
            name="cv_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="phd_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="doatap_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="course_plan_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="military_obligations_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="public_employee_permission_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="not_participated_declaration_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="eu_citizen_greek_language_certificate_document",
        ),
        migrations.RemoveField(
            model_name="application",
            name="responsible_declaration_document",
        ),
    ]
