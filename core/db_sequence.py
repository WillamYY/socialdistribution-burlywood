"""
Repair PostgreSQL sequences when they fall behind MAX(pk) (e.g. after data import).
"""


def repair_author_pk_sequence():
    from django.db import connection

    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('core_author', 'id'),
                COALESCE((SELECT MAX(id) FROM core_author), 0) + 1,
                false
            );
            """
        )
