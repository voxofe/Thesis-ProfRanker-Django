from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0064_profilepublication_sort_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="SjrLookup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("year", models.CharField(db_index=True, max_length=4)),
                ("issn_norm", models.CharField(db_index=True, max_length=16)),
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("country", models.CharField(blank=True, max_length=100, null=True)),
                ("sjr_quartile", models.CharField(blank=True, max_length=20, null=True)),
                ("source", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="sjrlookup",
            constraint=models.UniqueConstraint(
                fields=("year", "issn_norm"),
                name="unique_sjrlookup_year_issn",
            ),
        ),
        migrations.AddIndex(
            model_name="sjrlookup",
            index=models.Index(
                fields=["issn_norm", "year"],
                name="sjrlookup_issn_year_idx",
            ),
        ),
    ]
