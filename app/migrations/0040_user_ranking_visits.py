from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0039_position_closed_notified_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="ranking_visits",
            field=models.IntegerField(default=0),
        ),
    ]
