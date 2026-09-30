"""Curriculum resolution for a school year and grade level.

An explicit SchoolYearCurriculum row wins. Without one, the curriculum is the one
shared by the active programs at that grade level. Years are frozen (given explicit
rows) when they are snapshotted, so later program changes never rewrite history.
"""

from django.db.models import Q

from apps.school.models import Curriculum, Program, SchoolYear, SchoolYearCurriculum

GRADE_LEVELS = tuple(Program.GradeLevel.values)


def curriculum_for(school_year, grade_level):
    if school_year is None:
        return None
    row = (
        SchoolYearCurriculum.objects.filter(school_year=school_year, grade_level=grade_level)
        .select_related('curriculum')
        .first()
    )
    if row:
        return row.curriculum
    ids = set(
        Program.objects.filter(grade_level=grade_level, is_active=True, curriculum__isnull=False).values_list(
            'curriculum_id', flat=True
        )
    )
    if len(ids) == 1:
        return Curriculum.objects.filter(pk=ids.pop()).first()
    return None


def programs_for(school_year, grade_level, include_ids=()):
    """Programs offered at a grade level in a year, plus any extra ids that hold real records."""
    curriculum = curriculum_for(school_year, grade_level)
    offered = Q(grade_level=grade_level, is_active=True)
    if curriculum is not None:
        offered &= Q(curriculum=curriculum)
    return (
        Program.objects.filter(offered | Q(pk__in=list(include_ids)))
        .select_related('curriculum', 'continues_to')
        .order_by('sort_order', 'code')
    )


def set_year_curricula(school_year, mapping):
    """Save an explicit curriculum per grade level, e.g. {'Grade 12': <Curriculum>}."""
    for grade_level, curriculum in mapping.items():
        SchoolYearCurriculum.objects.update_or_create(
            school_year=school_year,
            grade_level=grade_level,
            defaults={'curriculum': curriculum},
        )


def carry_forward(school_year):
    """Give a new year the previous year's curriculum per grade level; the head teacher can change it."""
    previous = SchoolYear.objects.filter(label__lt=school_year.label).order_by('-label').first()
    for grade_level in GRADE_LEVELS:
        if SchoolYearCurriculum.objects.filter(school_year=school_year, grade_level=grade_level).exists():
            continue
        curriculum = curriculum_for(previous or school_year, grade_level)
        if curriculum is not None:
            SchoolYearCurriculum.objects.create(
                school_year=school_year,
                grade_level=grade_level,
                curriculum=curriculum,
            )


def freeze_year(school_year):
    """Record the resolved curriculum for each grade level so the year stays correct later."""
    for grade_level in GRADE_LEVELS:
        if SchoolYearCurriculum.objects.filter(school_year=school_year, grade_level=grade_level).exists():
            continue
        curriculum = curriculum_for(school_year, grade_level)
        if curriculum is not None:
            SchoolYearCurriculum.objects.create(
                school_year=school_year,
                grade_level=grade_level,
                curriculum=curriculum,
            )
