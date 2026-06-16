from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0059_scientificfield_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="last_resubmitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
