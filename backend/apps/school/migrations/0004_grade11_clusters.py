from django.db import migrations, models


PROGRAM_CHOICES = [
    ('STEM', 'STEM'),
    ('ABM', 'ABM'),
    ('HUMSS', 'HUMSS'),
    ('ICT', 'ICT'),
    ('HE', 'HE'),
    ('ASH', 'ASH'),
    ('BE', 'BE'),
    ('STEMC', 'STEMC'),
    ('HT', 'HT'),
    ('ICTP', 'ICTP'),
]


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0003_program_tvl_to_abm'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.CharField(choices=PROGRAM_CHOICES, max_length=16, unique=True),
        ),
    ]
