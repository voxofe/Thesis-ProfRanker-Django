from django.db import migrations, models


def copy_contact_fields(apps, schema_editor):
    User = apps.get_model("app", "User")
    UserProfile = apps.get_model("app", "UserProfile")

    for user in User.objects.all():
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.mobile_number = user.mobile_number
        profile.landline_number = user.landline_number
        profile.street_address = user.street_address
        profile.city = user.city
        profile.postal_code = user.postal_code
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0024_profiledocument_applicationdocument"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="mobile_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="landline_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="street_address",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="city",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(copy_contact_fields, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="mobile_number",
        ),
        migrations.RemoveField(
            model_name="user",
            name="landline_number",
        ),
        migrations.RemoveField(
            model_name="user",
            name="street_address",
        ),
        migrations.RemoveField(
            model_name="user",
            name="city",
        ),
        migrations.RemoveField(
            model_name="user",
            name="postal_code",
        ),
    ]
