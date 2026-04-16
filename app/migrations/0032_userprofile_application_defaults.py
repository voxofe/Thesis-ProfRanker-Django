from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0031_remove_vaultdocument_source_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_public_employee",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="is_eu_citizen_non_greek",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="has_not_participated_in_past_program",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phd_title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phd_acquisition_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phd_is_from_foreign_institute",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="work_experience",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="papers",
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
