from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='action_path',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='notification',
            name='level',
            field=models.CharField(
                choices=[('info', 'Info'), ('warning', 'Warning'), ('success', 'Success')],
                db_index=True,
                default='info',
                max_length=16,
            ),
        ),
    ]
