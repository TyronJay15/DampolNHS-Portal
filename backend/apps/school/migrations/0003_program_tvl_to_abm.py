from django.db import migrations, models


def rename_tvl_to_abm(apps, schema_editor):
    Program = apps.get_model('school', 'Program')
    Program.objects.filter(code='TVL').update(
        code='ABM',
        name='Accountancy, Business, and Management',
        summary='Prepares learners for college and careers in business, finance, accounting, and entrepreneurship.',
        description=(
            'ABM builds skills in accounting, business operations, and management. Learners study how '
            'organizations work, how money is recorded and used, and how to plan a small business, '
            'preparing them for business programs in college or for starting an enterprise.'
        ),
    )


def rename_abm_to_tvl(apps, schema_editor):
    Program = apps.get_model('school', 'Program')
    Program.objects.filter(code='ABM').update(code='TVL', name='Technical-Vocational-Livelihood')


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0002_program_gas_to_he'),
    ]

    operations = [
        migrations.RunPython(rename_tvl_to_abm, rename_abm_to_tvl),
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.CharField(
                choices=[
                    ('STEM', 'STEM'),
                    ('ABM', 'ABM'),
                    ('HUMSS', 'HUMSS'),
                    ('ICT', 'ICT'),
                    ('HE', 'HE'),
                ],
                max_length=16,
                unique=True,
            ),
        ),
    ]
