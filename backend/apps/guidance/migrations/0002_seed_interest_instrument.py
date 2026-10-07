from django.db import migrations


def seed(apps, schema_editor):
    from apps.guidance.instrument_seed import seed_instrument

    seed_instrument(apps.get_model)


class Migration(migrations.Migration):
    dependencies = [
        ('guidance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
