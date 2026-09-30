from decimal import Decimal

from django.apps import apps as django_apps

from apps.grading.college_catalog import COURSES, SHS_PROGRAMS


def seed_college_programs(get_model=None):
    """Create catalog college programs once, and fill SHS links that are still empty.

    Existing profiles and links (and admin edits) are left alone. On a fresh install the
    migration runs before setup_school creates SHS programs, so links are filled on a
    later run. Migration ml.0002 calls this with historical models, so it must only
    touch fields that exist at that migration.
    """
    get_model = get_model or django_apps.get_model
    college_model = get_model('ml', 'CollegeProgram')
    skill_model = get_model('ml', 'CollegeProgramSkill')
    domain_model = get_model('school', 'SkillDomain')
    program_model = get_model('school', 'Program')

    domains = {row.key: row for row in domain_model.objects.all()}
    programs = {row.code: row for row in program_model.objects.all()}
    created = 0
    for index, course in enumerate(COURSES, start=1):
        college, was_created = college_model.objects.get_or_create(
            code=course['code'],
            defaults={'name': course['name'], 'sort_order': index},
        )
        if not college.shs_programs.exists():
            college.shs_programs.set(
                [programs[code] for code in SHS_PROGRAMS.get(course['code'], ()) if code in programs]
            )
        if not was_created:
            continue
        created += 1
        floors = course.get('floors') or {}
        for key, level in course['profile'].items():
            if key not in domains:
                continue
            minimum = floors.get(key)
            skill_model.objects.create(
                college_program=college,
                domain=domains[key],
                level=Decimal(str(level)),
                minimum=Decimal(str(minimum)) if minimum is not None else None,
            )
    return created
