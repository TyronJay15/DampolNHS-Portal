from decimal import Decimal

from django.db import migrations


def add_research_levels(apps, schema_editor):
    """Gives existing college programs their catalog Research level, where they have none yet."""
    from apps.grading.college_catalog import COURSES

    domain = apps.get_model('school', 'SkillDomain').objects.filter(key='research').first()
    if domain is None:
        return
    college_model = apps.get_model('ml', 'CollegeProgram')
    skill_model = apps.get_model('ml', 'CollegeProgramSkill')
    for course in COURSES:
        level = course['profile'].get('research')
        college = college_model.objects.filter(code=course['code']).first()
        if level is None or college is None:
            continue
        skill_model.objects.get_or_create(
            college_program=college,
            domain=domain,
            defaults={'level': Decimal(str(level))},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('ml', '0002_college_programs_versioning'),
        ('school', '0011_research_domain'),
    ]

    operations = [
        migrations.RunPython(add_research_levels, migrations.RunPython.noop),
    ]
