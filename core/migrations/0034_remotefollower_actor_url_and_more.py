"""
ChatGPT, OpenAI, 2026-03-22, https://chatgpt.com/share/69c06f1d-df74-8329-a340-09d07835cfb1
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_remotefollower_actor_url_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="remotefollower",
                    name="actor_url",
                    field=models.URLField(blank=True, db_column="actor_url", max_length=500, null=True),
                ),
                migrations.AddField(
                    model_name="remotefollowrequest",
                    name="actor_url",
                    field=models.URLField(blank=True, db_column="actor_url", max_length=500, null=True),
                ),
            ],
        ),
    ]
