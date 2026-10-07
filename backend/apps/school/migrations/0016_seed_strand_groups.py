from django.db import migrations


def seed(apps, schema_editor):
    from apps.school.offerings import seed_strand_groups

    seed_strand_groups(apps.get_model)


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0015_program_strand_group'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
