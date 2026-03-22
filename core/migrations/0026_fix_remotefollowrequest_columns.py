# Fix armdb: table exists but has wrong/missing columns

from django.db import migrations


def add_columns(apps, schema_editor):
    """Add missing columns if they don't exist (fixes partial/broken 0025)."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='core_remotefollowrequest' AND column_name='actor_fqid') THEN
                    ALTER TABLE core_remotefollowrequest ADD COLUMN actor_fqid VARCHAR(500);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='core_remotefollowrequest' AND column_name='actor_display_name') THEN
                    ALTER TABLE core_remotefollowrequest ADD COLUMN actor_display_name VARCHAR(255) DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='core_remotefollowrequest' AND column_name='created_at') THEN
                    ALTER TABLE core_remotefollowrequest ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='core_remotefollowrequest' AND column_name='target_id') THEN
                    ALTER TABLE core_remotefollowrequest ADD COLUMN target_id INTEGER REFERENCES core_author(id) DEFERRABLE INITIALLY DEFERRED;
                END IF;
            END $$;
        """)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_remotefollowrequest'),
    ]

    operations = [
        migrations.RunPython(add_columns, noop),
    ]
