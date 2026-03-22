# Add actor_display_name to RemoteFollower for connections display

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_fix_remotefollower_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='remotefollower',
            name='actor_display_name',
            field=models.CharField(blank=True, default='Remote author', max_length=255),
        ),
    ]
