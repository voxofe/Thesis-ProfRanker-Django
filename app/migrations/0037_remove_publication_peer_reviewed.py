from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0036_publication_new_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="publication",
            name="peer_reviewed",
        ),
    ]
