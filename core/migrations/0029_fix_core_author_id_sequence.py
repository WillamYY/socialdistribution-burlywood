# Fixes stale core_author id sequence on PostgreSQL (duplicate key on insert).

from django.db import migrations


def fix_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('core_author', 'id'),
                COALESCE((SELECT MAX(id) FROM core_author), 0) + 1,
                false
            );
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_entrydelivery"),
    ]

    operations = [
        migrations.RunPython(fix_sequence, migrations.RunPython.noop),
    ]
