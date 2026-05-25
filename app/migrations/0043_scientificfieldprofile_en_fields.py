from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0042_scientificfieldprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="scientificfieldprofile",
            name="source_text_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="scientificfieldprofile",
            name="profile_text_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="scientificfieldprofile",
            name="keywords_en",
            field=models.JSONField(default=list),
        ),
    ]
