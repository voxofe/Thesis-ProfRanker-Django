from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0034_phd_degree"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Paper",
            new_name="Publication",
        ),
        migrations.RenameField(
            model_name="publication",
            old_name="paper_title",
            new_name="publication_title",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="paper_points",
            new_name="publication_points",
        ),
        migrations.AlterField(
            model_name="publication",
            name="application",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="publications",
                to="app.application",
            ),
        ),
    ]
