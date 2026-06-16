from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0058_add_updated_at_to_sf_and_embeddings"),
    ]

    operations = [
        migrations.AddField(
            model_name="scientificfield",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
    ]
