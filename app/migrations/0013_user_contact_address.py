from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0012_user_phone_number"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="phone_number",
        ),
        migrations.AddField(
            model_name="user",
            name="mobile_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="landline_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="street_address",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="city",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="postal_code",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
