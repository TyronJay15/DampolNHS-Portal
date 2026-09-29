"""Archive purge helpers with grade protection and optional hard delete."""

from django.db import transaction

from apps.grading.models import Grade
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import SchoolYear, Section


def section_delete_summary(section):
    return {
        'students': section.student_assignments.count(),
        'duties': section.teacher_assignments.count(),
        'grades': Grade.objects.filter(section=section).count(),
    }


def year_delete_summary(year):
    sections = year.sections.all()
    grade_count = Grade.objects.filter(school_year=year).count()
    return {
        'sections': sections.count(),
        'students': StudentSection.objects.filter(school_year=year).count(),
        'duties': TeacherAssignment.objects.filter(school_year=year).count(),
        'grades': grade_count,
    }


def purge_section(section, *, hard=False):
    summary = section_delete_summary(section)
    if not section.archived_at:
        return 'Archive this section before deleting it.', summary
    if summary['grades'] and not hard:
        return 'This section has grade records. Use hard delete with confirmation to remove them.', summary
    with transaction.atomic():
        Grade.objects.filter(section=section).delete()
        section.student_assignments.all().delete()
        section.teacher_assignments.all().delete()
        section.delete()
    return None, summary


def purge_school_year(year, *, hard=False):
    summary = year_delete_summary(year)
    if year.is_current:
        return 'The current school year cannot be deleted.', summary
    if not year.archived_at:
        return 'Archive this school year before deleting it.', summary
    if summary['grades'] and not hard:
        return 'This school year has grade records. Use hard delete with confirmation to remove them.', summary
    with transaction.atomic():
        for section in list(year.sections.all()):
            Grade.objects.filter(section=section).delete()
            section.student_assignments.all().delete()
            section.teacher_assignments.all().delete()
            section.delete()
        Grade.objects.filter(school_year=year).delete()
        StudentSection.objects.filter(school_year=year).delete()
        TeacherAssignment.objects.filter(school_year=year).delete()
        year.terms.all().delete()
        year.delete()
    return None, summary
