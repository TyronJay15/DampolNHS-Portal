"""Which terms each program subject runs in, per school year.

The admin's program subject list holds the default terms (empty means every term). When a
school year opens, the defaults are copied into that year's plan and the head teacher edits
it from there, so later default changes never rewrite an earlier year. A pair without a plan
row falls back to the default, and a subject outside the program list runs in every term,
so sections and grades from before the plan existed keep working unchanged.
"""

from apps.school.models import ProgramSubject, SubjectTermPlan
from apps.school.offerings import subject_payloads_for_program

TERM_NUMBERS = (1, 2, 3)


def clean_terms(value):
    """Sorted, de-duplicated term numbers. Raises ValueError for anything other than a list of 1-3."""
    if not isinstance(value, (list, tuple)):
        raise ValueError('terms must be a list.')
    numbers = set()
    for item in value:
        if isinstance(item, bool):
            raise ValueError('Terms are 1, 2, or 3.')
        try:
            number = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError('Terms are 1, 2, or 3.') from exc
        if number not in TERM_NUMBERS:
            raise ValueError('Terms are 1, 2, or 3.')
        numbers.add(number)
    return sorted(numbers)


def resolved(terms):
    """A stored term list as the terms it covers: empty means every term."""
    return tuple(sorted(terms)) if terms else TERM_NUMBERS


def seed_year_plan(school_year):
    """Copy the default terms into a year's plan. Rows the year already has are kept."""
    existing = set(
        SubjectTermPlan.objects.filter(school_year=school_year).values_list('program_id', 'subject_id')
    )
    SubjectTermPlan.objects.bulk_create(
        [
            SubjectTermPlan(
                school_year=school_year,
                program_id=row.program_id,
                subject_id=row.subject_id,
                terms=list(resolved(row.terms)),
            )
            for row in ProgramSubject.objects.only('program_id', 'subject_id', 'terms')
            if (row.program_id, row.subject_id) not in existing
        ]
    )


class TermPlan:
    """The resolved term plan of one school year. Load once, then ask per subject."""

    def __init__(self, school_year_id, program_ids=None):
        defaults = ProgramSubject.objects.only('program_id', 'subject_id', 'terms')
        plans = SubjectTermPlan.objects.filter(school_year_id=school_year_id)
        if program_ids is not None:
            defaults = defaults.filter(program_id__in=program_ids)
            plans = plans.filter(program_id__in=program_ids)
        self._terms = {(row.program_id, row.subject_id): resolved(row.terms) for row in defaults}
        self._terms.update({(row.program_id, row.subject_id): resolved(row.terms) for row in plans})

    def terms_for(self, program_id, subject_id):
        return list(self._terms.get((program_id, subject_id), TERM_NUMBERS))

    def runs_in(self, program_id, subject_id, term_number):
        return term_number in self._terms.get((program_id, subject_id), TERM_NUMBERS)


def scheduled_subject_payloads(program, school_year, plan=None):
    """The program's subjects, each with the terms it runs in during that school year."""
    if program is None:
        return []
    plan = plan or TermPlan(school_year.id if school_year else None, program_ids=[program.id])
    return [{**row, 'terms': plan.terms_for(program.id, row['id'])} for row in subject_payloads_for_program(program)]


def section_runs_subject(section, subject_id, term):
    """True when the subject is scheduled in this term for the section's program."""
    plan = TermPlan(term.school_year_id, program_ids=[section.program_id])
    return plan.runs_in(section.program_id, subject_id, term.number)


def not_scheduled_detail(subject, term):
    return {'detail': f'{subject.name} is not scheduled for {term.label}. Ask the Head Teacher to update the term plan.'}
