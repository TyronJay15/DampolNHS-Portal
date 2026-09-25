from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cms', '0002_announcement_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='kind',
            field=models.CharField(
                choices=[('news', 'News'), ('event', 'Event')],
                db_index=True,
                default='news',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='event_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='announcement',
            name='event_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='announcement',
            name='location',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
