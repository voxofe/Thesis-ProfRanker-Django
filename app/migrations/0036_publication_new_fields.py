from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0035_rename_paper_to_publication"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="authors",
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AddField(
            model_name="publication",
            name="publisher",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="publication",
            name="peer_reviewed",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
