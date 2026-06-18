from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0060_application_last_resubmitted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseplan",
            name="week_1",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_2",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_3",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_4",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_5",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_6",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_7",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_8",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_9",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_10",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_11",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_12",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="courseplan",
            name="week_13",
            field=models.TextField(blank=True, default=""),
        ),
    ]
