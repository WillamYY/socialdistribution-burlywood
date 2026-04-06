from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_fix_core_author_id_sequence"),
    ]

    operations = [
        migrations.AddField(
            model_name="author",
            name="listed_publicly",
            field=models.BooleanField(
                default=True,
                help_text="If false, this account is omitted from the public author directory and API list.",
            ),
        ),
    ]
