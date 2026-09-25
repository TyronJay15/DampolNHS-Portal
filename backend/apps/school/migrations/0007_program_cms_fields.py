from django.db import migrations, models


def copy_catalog_copy(apps, schema_editor):
    Program = apps.get_model('school', 'Program')
    from apps.school.program_catalog import PROGRAMS

    catalog = {item['code']: item for item in PROGRAMS}
    for program in Program.objects.all():
        item = catalog.get(program.code)
        if not item:
            continue
        details = item.get('details') or {}
        program.grade_level = program.grade_level or item.get('grade_level') or ''
        program.track = program.track or details.get('track') or ''
        if not program.pathways:
            program.pathways = list(details.get('pathways') or [])
        program.save(update_fields=['grade_level', 'track', 'pathways'])


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0006_term_encode_window'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='grade_level',
            field=models.CharField(
                blank=True,
                choices=[('Grade 11', 'Grade 11'), ('Grade 12', 'Grade 12')],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='program',
            name='pathways',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='program',
            name='track',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.CharField(max_length=16, unique=True),
        ),
        migrations.RunPython(copy_catalog_copy, migrations.RunPython.noop),
    ]
