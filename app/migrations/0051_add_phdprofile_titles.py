from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0050_phd_profile_embedding"),
    ]

    operations = [
        migrations.AddField(
            model_name="phdprofile",
            name="title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="phdprofile",
            name="title_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
