from django.db import migrations


def seed(apps, schema_editor):
    from apps.guidance.instrument_seed import seed_dampol_instrument

    seed_dampol_instrument(apps.get_model)


class Migration(migrations.Migration):
    dependencies = [
        ('guidance', '0002_seed_interest_instrument'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
