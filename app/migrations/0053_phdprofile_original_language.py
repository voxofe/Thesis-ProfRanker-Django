from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0052_merge_20260529_2009"),
    ]

    operations = [
        migrations.AddField(
            model_name="phdprofile",
            name="original_language",
            field=models.CharField(
                blank=True,
                choices=[("gr", "Greek"), ("en", "English")],
                max_length=2,
                null=True,
            ),
        ),
    ]
