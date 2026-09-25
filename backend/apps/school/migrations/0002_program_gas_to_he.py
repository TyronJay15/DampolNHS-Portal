from django.db import migrations, models


def rename_gas_to_he(apps, schema_editor):
    Program = apps.get_model('school', 'Program')
    Program.objects.filter(code='GAS').update(
        code='HE',
        name='Home Economics',
        summary='Culinary arts, tourism, hospitality, and fashion — practical skills for work, TESDA, or further study.',
        description=(
            'Home Economics is a TVL strand. Learners train in food, hospitality, and related services '
            'through hands-on work and work immersion. Many specializations also prepare learners for '
            'TESDA competency assessments.'
        ),
    )


def rename_he_to_gas(apps, schema_editor):
    Program = apps.get_model('school', 'Program')
    Program.objects.filter(code='HE').update(code='GAS', name='General Academic Strand')


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(rename_gas_to_he, rename_he_to_gas),
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.CharField(
                choices=[
                    ('STEM', 'STEM'),
                    ('TVL', 'TVL'),
                    ('HUMSS', 'HUMSS'),
                    ('ICT', 'ICT'),
                    ('HE', 'HE'),
                ],
                max_length=16,
                unique=True,
            ),
        ),
    ]
