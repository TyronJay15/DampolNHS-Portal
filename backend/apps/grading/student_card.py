from collections import defaultdict
from decimal import Decimal

from apps.accounts.models import StudentProfile
from apps.grading.advisory import section_subject_assignments
from apps.grading.models import Grade
from apps.grading.recommend import recommend_payload
from apps.grading.scores import average
from apps.people.models import Registration, StudentSection
from apps.school.models import SchoolYear, Term
from apps.school.offerings import subject_payloads_for_program, subject_rows_for_program


def _placement(profile):
    return (
        StudentSection.objects.filter(student=profile, is_active=True)
        .select_related('section', 'section__program', 'school_year')
        .first()
    )


def _program(profile, placement):
    if placement and placement.section.program_id:
        return placement.section.program
    registration = (
        Registration.objects.filter(user=profile.user)
        .select_related('program')
        .first()
    )
    return registration.program if registration else None


def _year(placement):
    if placement:
        return placement.school_year
    return SchoolYear.objects.filter(is_current=True).first()


def _subjects(section, program):
    assigned = section_subject_assignments(section) if section else []
    if not assigned:
        return subject_payloads_for_program(program)

    catalog = {row.subject_id: row for row in subject_rows_for_program(program)}
    rows = []
    for item in assigned:
        link = catalog.get(item.subject_id)
        rows.append(
            {
                'id': item.subject_id,
                'code': item.subject.code,
                'name': item.subject.name,
                'kind': link.kind if link else '',
                'term': link.term if link else None,
            }
        )
    return rows


def _append_released_subjects(subjects, grades):
    known = {row['id'] for row in subjects}
    for grade in grades:
        if grade.subject_id in known:
            continue
        subjects.append(
            {
                'id': grade.subject_id,
                'code': grade.subject.code,
                'name': grade.subject.name,
                'kind': '',
                'term': None,
            }
        )
        known.add(grade.subject_id)
    return subjects


def _summary(values, possible):
    """Coverage-aware average. `possible` is the offered cells for that row or column."""
    mean = average(values)
    return {
        'average': str(mean) if mean is not None else None,
        'included': len(values),
        'possible': possible,
    }


def _offered_terms(subject, terms):
    numbers = [term.number for term in terms]
    offered = subject.get('term')
    if offered in numbers:
        return {offered}
    return set(numbers)


def _averages(released, subjects, terms):
    """Subject, term, and overall averages from released scores only. Missing cells are skipped."""
    by_subject = defaultdict(list)
    by_term = defaultdict(list)
    scored_terms = defaultdict(set)
    scored_subjects = defaultdict(set)
    for grade in released:
        score = Decimal(str(grade.score))
        by_subject[grade.subject_id].append(score)
        by_term[grade.term.number].append(score)
        scored_terms[grade.subject_id].add(grade.term.number)
        scored_subjects[grade.term.number].add(grade.subject_id)

    subject_rows = []
    for row in subjects:
        offered = _offered_terms(row, terms)
        possible = max(len(offered), len(scored_terms.get(row['id'], ())))
        subject_rows.append(
            {'subject_id': row['id'], **_summary(by_subject.get(row['id'], []), possible)}
        )

    term_rows = []
    for term in terms:
        offered = {row['id'] for row in subjects if term.number in _offered_terms(row, terms)}
        possible = len(offered | scored_subjects.get(term.number, set()))
        term_rows.append(
            {'term_number': term.number, **_summary(by_term.get(term.number, []), possible)}
        )

    every_score = [score for values in by_subject.values() for score in values]
    return {
        'subject_averages': subject_rows,
        'term_averages': term_rows,
        'overall_average': _summary(every_score, sum(row['possible'] for row in subject_rows)),
    }


def student_grade_card(profile: StudentProfile):
    placement = _placement(profile)
    program = _program(profile, placement)
    year = _year(placement)
    section = placement.section if placement else None
    terms = list(Term.objects.filter(school_year=year).order_by('number')) if year else []

    released = list(
        Grade.objects.filter(student=profile, status=Grade.Status.RELEASED)
        .filter(**({'school_year': year} if year else {}))
        .select_related('subject', 'term')
        .order_by('term__number', 'subject__name')
    )
    subjects = _append_released_subjects(_subjects(section, program), released)

    return {
        'school_year': year.label if year else '',
        'terms': [{'id': term.id, 'number': term.number, 'label': term.label} for term in terms],
        'subjects': subjects,
        'grades': [
            {
                'id': grade.id,
                'subject_id': grade.subject_id,
                'subject': grade.subject.name,
                'term': grade.term.label,
                'term_number': grade.term.number,
                'score': str(grade.score),
            }
            for grade in released
        ],
        **_averages(released, subjects, terms),
        'recommendation': recommend_payload(released) if released else None,
    }
