"""
ChatGPT, OpenAI, 2026-03-22, https://chatgpt.com/share/69c06f1d-df74-8329-a340-09d07835cfb1
"""
from django.db import migrations, models


TABLE_NAME = "core_remotefollower"


def _table_exists(schema_editor, table_name):
    return table_name in schema_editor.connection.introspection.table_names()


def _column_exists(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(col.name == column_name for col in description)


def add_columns(apps, schema_editor):
    """Add missing columns to core_remotefollower if they don't exist."""
    if not _table_exists(schema_editor, TABLE_NAME):
        return

    RemoteFollower = apps.get_model("core", "RemoteFollower")

    if not _column_exists(schema_editor, TABLE_NAME, "actor_fqid"):
        field = models.URLField(max_length=500, null=True, blank=True)
        field.set_attributes_from_name("actor_fqid")
        schema_editor.add_field(RemoteFollower, field)

    if not _column_exists(schema_editor, TABLE_NAME, "created_at"):
        field = models.DateTimeField(auto_now_add=True, null=True)
        field.set_attributes_from_name("created_at")
        schema_editor.add_field(RemoteFollower, field)

    if not _column_exists(schema_editor, TABLE_NAME, "target_id"):
        field = models.ForeignKey(
            to="core.author",
            on_delete=models.CASCADE,
            related_name="+",
            null=True,
        )
        field.set_attributes_from_name("target")
        schema_editor.add_field(RemoteFollower, field)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0027_remotefollower"),
    ]

    operations = [
        migrations.RunPython(add_columns, noop),
    ]
