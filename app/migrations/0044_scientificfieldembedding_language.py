from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0043_scientificfieldprofile_en_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="scientificfieldembedding",
            name="language",
            field=models.CharField(choices=[("gr", "Greek"), ("en", "English")], default="gr", max_length=2),
        ),
    ]
