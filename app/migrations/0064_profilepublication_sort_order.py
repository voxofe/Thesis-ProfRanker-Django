from django.db import migrations, models


def backfill_sort_order(apps, schema_editor):
    ProfilePublication = apps.get_model("app", "ProfilePublication")
    user_ids = (
        ProfilePublication.objects.order_by()
        .values_list("user_id", flat=True)
        .distinct()
    )

    for user_id in user_ids:
        publications = list(
            ProfilePublication.objects.filter(user_id=user_id)
            .order_by("-updated_at", "-id")
        )
        for position, publication in enumerate(publications, start=1):
            publication.sort_order = position
            publication.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0063_merge_20260621_1254"),
    ]

    operations = [
        migrations.AddField(
            model_name="profilepublication",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_sort_order, migrations.RunPython.noop),
    ]
