from django.db import migrations, models


def seed_section_status(apps, schema_editor):
    Section = apps.get_model('school', 'Section')
    StudentSection = apps.get_model('people', 'StudentSection')
    TeacherAssignment = apps.get_model('people', 'TeacherAssignment')

    for section in Section.objects.all():
        if section.archived_at:
            section.status = 'archived'
        else:
            has_students = StudentSection.objects.filter(section_id=section.id, is_active=True).exists()
            has_duties = TeacherAssignment.objects.filter(
                section_id=section.id,
                status='active',
            ).exists()
            if has_students or has_duties:
                section.status = 'active'
            else:
                section.status = 'draft'
        section.capacity = section.capacity or 40
        section.save(update_fields=['status', 'capacity'])


class Migration(migrations.Migration):
    dependencies = [
        ('people', '0001_initial'),
        ('school', '0008_archive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='section',
            name='capacity',
            field=models.PositiveSmallIntegerField(default=40),
        ),
        migrations.AddField(
            model_name='section',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('in_progress', 'In progress'),
                    ('ready', 'Ready'),
                    ('active', 'Active'),
                    ('archived', 'Archived'),
                ],
                db_index=True,
                default='draft',
                max_length=16,
            ),
        ),
        migrations.RunPython(seed_section_status, migrations.RunPython.noop),
    ]
