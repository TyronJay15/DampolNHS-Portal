from apps.school.models import Program, ProgramSubject, Subject
from apps.school.program_catalog import PROGRAMS
from apps.school.subject_catalog import LEGACY_SUBJECT_CODES, PROGRAM_SUBJECTS, SUBJECTS


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
        ProgramSubject.objects.create(program=program, subject=subject, kind=kind, term=term)
        created += 1
    return created


def sync_subject_catalog():
    Subject.objects.filter(code__in=LEGACY_SUBJECT_CODES).update(is_active=False)
    for code, name in SUBJECTS:
        Subject.objects.update_or_create(code=code, defaults={'name': name, 'is_active': True})
    return _seed_empty_program_subjects()


def replace_program_subjects(program, rows):
    ProgramSubject.objects.filter(program=program).delete()
    ProgramSubject.objects.bulk_create(
        [
            ProgramSubject(
                program=program,
                subject_id=row['subject_id'],
                kind=row['kind'],
                term=row['term'],
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
        .order_by('kind', 'term', 'subject__name')
    )


def subject_payloads_for_program(program):
    return [
        {
            'id': row.subject_id,
            'code': row.subject.code,
            'name': row.subject.name,
            'kind': row.kind,
            'term': row.term,
        }
        for row in subject_rows_for_program(program)
    ]


def program_offers_subject(program, subject):
    if program is None or subject is None:
        return False
    return ProgramSubject.objects.filter(program=program, subject=subject).exists()
