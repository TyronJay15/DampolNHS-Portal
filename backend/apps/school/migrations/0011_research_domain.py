from django.db import migrations


def add_research_domain(apps, schema_editor):
    """Adds the Research domain and links the research subjects (fills blanks only)."""
    from apps.school.offerings import seed_academic_reference

    seed_academic_reference(apps.get_model)


class Migration(migrations.Migration):
    dependencies = [
        ('school', '0010_curriculum_skill_domains'),
    ]

    operations = [
        migrations.RunPython(add_research_domain, migrations.RunPython.noop),
    ]
