"""Reading and saving a school year's term plan, shared by the Head Teacher's screen and access requests.

Grades are never moved or deleted here. Saving a plan that leaves grades outside it is allowed;
the result counts them so the screen can say so, and those grades stay visible everywhere.
"""

from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.audit import services as audit
from apps.grading.models import Grade
from apps.people.scope import require_grade_in_scope
from apps.school.curriculum import GRADE_LEVELS, programs_for
from apps.school.models import Program, ProgramSubject, Section, SubjectTermPlan
from apps.school.term_plan import TermPlan, clean_terms

MAX_ROWS = 500


def _programs(year, levels):
    """Programs offered in the year at these grade levels (None for all), plus any that hold sections."""
    programs = {}
    for level in GRADE_LEVELS:
        if levels is not None and level not in levels:
            continue
        in_use = Section.objects.filter(school_year=year, grade_level=level).exclude(program=None)
        for program in programs_for(year, level, include_ids=in_use.values_list('program_id', flat=True)):
            programs.setdefault(program.id, program)
    return list(programs.values())


def _graded_terms(year, program_ids):
    graded = defaultdict(set)
    rows = (
        Grade.objects.filter(school_year=year, section__program_id__in=program_ids)
        .values_list('section__program_id', 'subject_id', 'term__number')
        .distinct()
    )
    for program_id, subject_id, number in rows:
        graded[(program_id, subject_id)].add(number)
    return graded


def plan_payload(year, levels):
    """The plan for the programs at these grade levels (None for every level)."""
    programs = _programs(year, levels)
    ids = [program.id for program in programs]
    plan = TermPlan(year.id, program_ids=ids)
    graded = _graded_terms(year, ids)
    links = defaultdict(list)
    for link in (
        ProgramSubject.objects.filter(program_id__in=ids, subject__is_active=True)
        .select_related('subject')
        .order_by('kind', 'subject__name')
    ):
        links[link.program_id].append(link)
    return {
        'school_year': {'id': year.id, 'label': year.label, 'editable': year.archived_at is None},
        'programs': [
            {
                'id': program.id,
                'code': program.code,
                'name': program.name,
                'grade_level': program.grade_level,
                'subjects': [
                    {
                        'subject_id': link.subject_id,
                        'code': link.subject.code,
                        'name': link.subject.name,
                        'kind': link.kind,
                        'terms': plan.terms_for(program.id, link.subject_id),
                        'graded_terms': sorted(graded.get((program.id, link.subject_id), ())),
                    }
                    for link in links[program.id]
                ],
            }
            for program in programs
        ],
    }


def clean_rows(rows, user):
    """Validated {(program_id, subject_id): terms}. Raises ValueError with a message for the screen."""
    if not isinstance(rows, list) or not rows:
        raise ValueError('Nothing to save.')
    if len(rows) > MAX_ROWS:
        raise ValueError(f'Save at most {MAX_ROWS} subjects at a time.')
    cleaned = {}
    programs = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each row needs a program, a subject and its terms.')
        try:
            program_id, subject_id = int(row.get('program')), int(row.get('subject'))
        except (TypeError, ValueError) as exc:
            raise ValueError('Each row needs a program, a subject and its terms.') from exc
        if program_id not in programs:
            programs[program_id] = get_object_or_404(Program, pk=program_id)
            require_grade_in_scope(user, programs[program_id].grade_level)
        link = ProgramSubject.objects.filter(program_id=program_id, subject_id=subject_id).select_related('subject').first()
        if link is None:
            raise ValueError(f'That subject is not on the {programs[program_id].code} subject list.')
        terms = clean_terms(row.get('terms'))
        if not terms:
            raise ValueError(f'Pick at least one term for {link.subject.name} ({programs[program_id].code}).')
        cleaned[(program_id, subject_id)] = terms
    return cleaned


def _outside_count(year, cleaned):
    """Grades of the saved subjects that sit in a term the new plan leaves out. They are kept."""
    total = 0
    for (program_id, subject_id), terms in cleaned.items():
        total += (
            Grade.objects.filter(school_year=year, section__program_id=program_id, subject_id=subject_id)
            .exclude(term__number__in=terms)
            .count()
        )
    return total


def save_term_plan(year, rows, actor):
    """Save the changed rows of a year's plan. Raises ValueError with a message for the screen."""
    if year.archived_at is not None:
        raise ValueError('Restore this school year before changing its term plan.')
    cleaned = clean_rows(rows, actor)
    before = TermPlan(year.id, program_ids={program_id for program_id, _subject in cleaned})
    changed = []
    with transaction.atomic():
        for (program_id, subject_id), terms in cleaned.items():
            previous = before.terms_for(program_id, subject_id)
            if previous == terms:
                continue
            SubjectTermPlan.objects.update_or_create(
                school_year=year,
                program_id=program_id,
                subject_id=subject_id,
                defaults={'terms': terms},
            )
            changed.append({'program': program_id, 'subject': subject_id, 'from': previous, 'to': terms})
        outside = _outside_count(year, {(row['program'], row['subject']): row['to'] for row in changed})
        if changed:
            audit.record(
                user=actor,
                action='term_plan_saved',
                summary=f'Updated the term plan for {year.label} ({len(changed)} subject(s))',
                target_type='SchoolYear',
                target_id=year.id,
                details={'changed': changed, 'grades_outside_plan': outside},
            )
    return {'saved': len(changed), 'outside': outside}
