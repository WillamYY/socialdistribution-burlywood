# Generated manually for User Story #5 - GitHub activity sync

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0005_delete_comment_delete_like'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='github_event_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True),
        ),
    ]
