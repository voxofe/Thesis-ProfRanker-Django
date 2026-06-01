from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0053_phdprofile_original_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="phd_cosine_similarity",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
