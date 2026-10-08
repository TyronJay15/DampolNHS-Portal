from django.db import migrations, models


def keep_current_places(apps, schema_editor):
    """Existing posts keep showing where they did before: events were on dashboards and the website ("both"); news
    was website-only, which the field's default already says. No record is deleted or otherwise changed."""
    announcement = apps.get_model('cms', 'Announcement')
    announcement.objects.filter(kind='event').update(publish_to='both')


class Migration(migrations.Migration):
    dependencies = [
        ('cms', '0003_announcement_events'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='publish_to',
            field=models.CharField(
                choices=[('website', 'Website'), ('dashboard', 'Dashboard'), ('both', 'Both')],
                db_index=True,
                default='website',
                max_length=16,
            ),
        ),
        migrations.RunPython(keep_current_places, migrations.RunPython.noop),
    ]
