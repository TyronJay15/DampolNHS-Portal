from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0007_program_cms_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolyear',
            name='archived_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='section',
            name='archived_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
