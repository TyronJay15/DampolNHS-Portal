from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('guidance', '0005_open_dampol_shs_instrument'),
    ]

    operations = [
        migrations.DeleteModel(name='TrainingJob'),
        migrations.DeleteModel(name='TrainingSnapshot'),
    ]
