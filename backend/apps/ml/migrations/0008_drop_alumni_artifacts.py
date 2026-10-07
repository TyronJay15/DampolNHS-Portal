from django.db import migrations


ALUMNI_ROLES = ('recommender_family', 'recommender_program')


def drop_alumni_runs(apps, schema_editor):
    ModelRun = apps.get_model('ml', 'ModelRun')
    ModelRun.objects.filter(name__in=ALUMNI_ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ml', '0007_seed_recommender'),
    ]

    operations = [
        migrations.DeleteModel(name='ModelArtifact'),
        migrations.RunPython(drop_alumni_runs, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='modelrun',
            options={'ordering': ['-trained_at']},
        ),
    ]
