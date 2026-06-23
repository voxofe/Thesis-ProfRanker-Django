from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0065_sjrlookup"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="theme_mode",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark")],
                default="light",
                max_length=5,
            ),
        ),
    ]
