"""
ChatGPT, OpenAI, 2026-03-22, https://chatgpt.com/share/69c06f1d-df74-8329-a340-09d07835cfb1
"""
from django.db import migrations, models


TABLE_NAME = "core_remotefollowrequest"


def _table_exists(schema_editor, table_name):
    return table_name in schema_editor.connection.introspection.table_names()


def _column_exists(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(col.name == column_name for col in description)


def add_actor_url_if_missing(apps, schema_editor):
    """Add actor_url column only if it doesn't exist."""
    if not _table_exists(schema_editor, TABLE_NAME):
        return

    if _column_exists(schema_editor, TABLE_NAME, "actor_url"):
        return

    RemoteFollowRequest = apps.get_model("core", "RemoteFollowRequest")
    field = models.URLField(max_length=500, blank=True, null=True, db_column="actor_url")
    field.set_attributes_from_name("actor_url")
    schema_editor.add_field(RemoteFollowRequest, field)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_remotefollower_actor_display_name"),
    ]

    operations = [
        migrations.RunPython(add_actor_url_if_missing, noop),
    ]
