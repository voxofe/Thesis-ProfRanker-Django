from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0048_merge_0047_phd_check_0047_remove_userprofile_phd_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="phd_abstract",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="application",
            name="phd_keywords",
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AddField(
            model_name="phddegree",
            name="abstract",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="phddegree",
            name="keywords",
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.DeleteModel(
            name="PhdCheck",
        ),
        migrations.DeleteModel(
            name="PhdDocument",
        ),
    ]
