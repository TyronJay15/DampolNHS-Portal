from django.db import migrations


def drop_synthetic_runs(apps, schema_editor):
    """Removes saved 'knn' runs: they were trained on noisy copies of the course profiles, not on students.

    Recommendations now compare against CollegeProgram profiles directly, and nothing reads these rows.
    """
    apps.get_model('ml', 'ModelRun').objects.filter(name='knn').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ml', '0003_research_levels'),
    ]

    operations = [
        migrations.RunPython(drop_synthetic_runs, migrations.RunPython.noop),
    ]
