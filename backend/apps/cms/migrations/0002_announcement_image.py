from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cms', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='image',
            field=models.CharField(blank=True, max_length=400),
        ),
    ]
