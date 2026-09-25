from django.db import migrations, models


def locked_to_approved(apps, schema_editor):
    Grade = apps.get_model('grading', 'Grade')
    History = apps.get_model('grading', 'GradeHistory')
    Grade.objects.filter(status='locked').update(status='approved')
    History.objects.filter(from_status='locked').update(from_status='approved')
    History.objects.filter(to_status='locked').update(to_status='approved')


def approved_to_locked(apps, schema_editor):
    Grade = apps.get_model('grading', 'Grade')
    History = apps.get_model('grading', 'GradeHistory')
    Grade.objects.filter(status='approved').update(status='locked')
    History.objects.filter(from_status='approved').update(from_status='locked')
    History.objects.filter(to_status='approved').update(to_status='locked')


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0002_drop_ptpa_tables'),
    ]

    operations = [
        migrations.RunPython(locked_to_approved, approved_to_locked),
        migrations.AlterField(
            model_name='grade',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted'),
                    ('approved', 'Approved'),
                    ('released', 'Released'),
                ],
                db_index=True,
                default='draft',
                max_length=16,
            ),
        ),
        migrations.RenameField(
            model_name='grade',
            old_name='locked_at',
            new_name='approved_at',
        ),
    ]
