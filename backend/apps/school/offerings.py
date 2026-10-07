from django.apps import apps as django_apps

from apps.school.models import Program, ProgramSubject, Subject
from apps.school.program_catalog import CURRICULA, CURRICULUM_BY_GRADE, GRADE11_TO_GRADE12, PROGRAMS, STRAND_GROUPS
from apps.school.subject_catalog import (
    LEGACY_SUBJECT_CODES,
    MATCHING_EXCLUDED,
    PROGRAM_SUBJECTS,
    SKILL_DOMAINS,
    SUBJECT_DOMAIN,
    SUBJECTS,
)


def program_seed_defaults(item):
    details = item.get('details') or {}
    return {
        'name': item['name'],
        'summary': item.get('summary', ''),
        'description': item.get('description', ''),
        'sort_order': item.get('sort_order', 0),
        'is_active': True,
        'track': details.get('track', ''),
        'grade_level': item.get('grade_level', ''),
        'pathways': list(details.get('pathways') or []),
    }


def seed_programs():
    """Create catalog programs. Never overwrite CMS-edited copy."""
    created = 0
    for item in PROGRAMS:
        program, was_created = Program.objects.get_or_create(
            code=item['code'],
            defaults=program_seed_defaults(item),
        )
        if was_created:
            created += 1
            continue
        updates = {}
        details = item.get('details') or {}
        if not program.grade_level:
            updates['grade_level'] = item.get('grade_level', '')
        if not program.track:
            updates['track'] = details.get('track', '')
        if not program.pathways:
            updates['pathways'] = list(details.get('pathways') or [])
        if updates:
            for field, value in updates.items():
                setattr(program, field, value)
            program.save(update_fields=list(updates))
    return created


def _seed_empty_program_subjects():
    subjects = {row.code: row for row in Subject.objects.filter(is_active=True)}
    programs = {row.code: row for row in Program.objects.all()}
    linked = set(Program.objects.filter(program_subjects__isnull=False).values_list('code', flat=True))
    created = 0
    for program_code, subject_code, kind, term in PROGRAM_SUBJECTS:
        if program_code in linked:
            continue
        program = programs.get(program_code)
        subject = subjects.get(subject_code)
        if program is None or subject is None:
            continue
        ProgramSubject.objects.create(program=program, subject=subject, kind=kind, terms=[term] if term else [])
        created += 1
    return created


def sync_subject_catalog():
    Subject.objects.filter(code__in=LEGACY_SUBJECT_CODES).update(is_active=False)
    for code, name in SUBJECTS:
        Subject.objects.update_or_create(code=code, defaults={'name': name, 'is_active': True})
    return _seed_empty_program_subjects()


def seed_academic_reference(get_model=None):
    """Seed curricula, skill domains, program curriculum/continuation and subject domains.

    Fills blanks only, so admin edits are kept. Migration school.0010 calls this with
    historical models, so it must only touch fields that exist at that migration.
    """
    get_model = get_model or django_apps.get_model
    curriculum_model = get_model('school', 'Curriculum')
    domain_model = get_model('school', 'SkillDomain')
    program_model = get_model('school', 'Program')
    subject_model = get_model('school', 'Subject')

    curricula = {}
    for item in CURRICULA:
        curricula[item['code']], _created = curriculum_model.objects.get_or_create(
            code=item['code'],
            defaults={'name': item['name'], 'sort_order': item['sort_order']},
        )

    domains = {}
    for index, (key, label) in enumerate(SKILL_DOMAINS, start=1):
        domains[key], _created = domain_model.objects.get_or_create(
            key=key,
            defaults={'label': label, 'sort_order': index},
        )

    for grade_level, code in CURRICULUM_BY_GRADE.items():
        program_model.objects.filter(grade_level=grade_level, curriculum__isnull=True).update(
            curriculum=curricula[code]
        )

    by_code = {row.code: row for row in program_model.objects.all()}
    for cluster, strand in GRADE11_TO_GRADE12.items():
        program = by_code.get(cluster)
        target = by_code.get(strand)
        if program is not None and target is not None and program.continues_to_id is None:
            program.continues_to = target
            program.save(update_fields=['continues_to'])

    for code, key in SUBJECT_DOMAIN.items():
        subject_model.objects.filter(code=code, skill_domain__isnull=True).update(skill_domain=domains[key])


def seed_matching_exclusions(get_model=None):
    """Mark catalog subjects that are deliberately left out of college matching.

    Separate from seed_academic_reference because the field only exists from
    migration school.0012 on, and older migrations call that function.
    """
    get_model = get_model or django_apps.get_model
    get_model('school', 'Subject').objects.filter(
        code__in=MATCHING_EXCLUDED,
        skill_domain__isnull=True,
    ).update(matching_excluded=True)


def seed_strand_groups(get_model=None):
    """Give each catalog SHS program its strand group, where it has none yet.

    Migration school.0016 calls this with historical models, so it must only touch fields that exist there.
    """
    get_model = get_model or django_apps.get_model
    program_model = get_model('school', 'Program')
    for code, group in STRAND_GROUPS.items():
        program_model.objects.filter(code=code, strand_group='').update(strand_group=group)


def replace_program_subjects(program, rows):
    ProgramSubject.objects.filter(program=program).delete()
    ProgramSubject.objects.bulk_create(
        [
            ProgramSubject(
                program=program,
                subject_id=row['subject_id'],
                kind=row['kind'],
                terms=row['terms'],
            )
            for row in rows
        ]
    )


def subject_rows_for_program(program):
    if program is None:
        return []
    return list(
        ProgramSubject.objects.filter(program=program, subject__is_active=True)
        .select_related('subject')
        .order_by('kind', 'subject__name')
    )


def subject_payloads_for_program(program):
    return [
        {
            'id': row.subject_id,
            'code': row.subject.code,
            'name': row.subject.name,
            'kind': row.kind,
            'terms': row.terms,
        }
        for row in subject_rows_for_program(program)
    ]


def program_offers_subject(program, subject):
    if program is None or subject is None:
        return False
    return ProgramSubject.objects.filter(program=program, subject=subject).exists()
