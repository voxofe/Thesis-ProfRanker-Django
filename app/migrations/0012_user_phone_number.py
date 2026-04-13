from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0011_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
