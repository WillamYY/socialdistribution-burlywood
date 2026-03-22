# Add actor_url for armdb compatibility (column may already exist)

from django.db import migrations


def add_actor_url_if_missing(apps, schema_editor):
    """Add actor_url column only if it doesn't exist."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='core_remotefollowrequest' AND column_name='actor_url') THEN
                    ALTER TABLE core_remotefollowrequest ADD COLUMN actor_url VARCHAR(500);
                END IF;
            END $$;
        """)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_remotefollower_actor_display_name'),
    ]

    operations = [
        migrations.RunPython(add_actor_url_if_missing, noop),
    ]
