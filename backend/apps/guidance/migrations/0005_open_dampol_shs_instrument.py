from django.db import migrations


def apply(apps, schema_editor):
    from apps.guidance.instrument_seed import open_dampol_instrument

    open_dampol_instrument(apps.get_model)


class Migration(migrations.Migration):
    dependencies = [
        ('guidance', '0004_training_snapshot'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
