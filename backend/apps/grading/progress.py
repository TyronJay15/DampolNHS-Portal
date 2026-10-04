"""Encode and card-progress labels shared by teacher, HT, and adviser views."""

from collections import defaultdict

from django.db.models import Count, Max, Q

from apps.accounts.lifecycle import HIDDEN
from apps.grading.models import Grade
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Section, Term
from apps.school.term_plan import TermPlan


def describe_counts(roster, *, missing, draft, submitted, approved, released, updated_at=None):
    roster = int(roster or 0)
    missing = int(missing or 0)
    draft = int(draft or 0)
    submitted = int(submitted or 0)
    approved = int(approved or 0)
    released = int(released or 0)
    encoded = max(roster - missing, 0)
    if roster <= 0:
        progress = 'empty'
        progress_label = 'No students'
    elif missing >= roster:
        progress = 'not_encoded'
        progress_label = 'Not encoded'
    elif missing > 0:
        progress = 'in_progress'
        progress_label = f'In progress {encoded}/{roster}'
    else:
        progress = 'encoded'
        progress_label = 'Encoded'

    if released:
        if roster and released >= roster and missing == 0:
            workflow, workflow_label = 'shown', 'Shown'
        else:
            workflow, workflow_label = 'shown', f'Shown {released}/{roster}' if roster else 'Shown'
    elif approved:
        workflow, workflow_label = 'approved', 'Approved'
    elif submitted:
        workflow, workflow_label = 'submitted', 'Submitted'
    elif draft:
        workflow, workflow_label = 'draft', 'Ready to submit'
    else:
        workflow, workflow_label = '', ''

    return {
        'roster': roster,
        'encoded': encoded,
        'missing': missing,
        'draft': draft,
        'submitted': submitted,
        'approved': approved,
        'released': released,
        'progress': progress,
        'progress_label': progress_label,
        'workflow': workflow,
        'workflow_label': workflow_label,
        'updated_at': updated_at,
    }


def pack_counts(roster, draft=0, submitted=0, approved=0, released=0, updated_at=None):
    used = draft + submitted + approved + released
    missing = max(int(roster or 0) - used, 0)
    payload = describe_counts(
        roster,
        missing=missing,
        draft=draft,
        submitted=submitted,
        approved=approved,
        released=released,
        updated_at=updated_at,
    )
    payload['draft'] = int(draft or 0)
    payload['submitted'] = int(submitted or 0)
    payload['approved'] = int(approved or 0)
    payload['released'] = int(released or 0)
    return payload


def _current_term(terms):
    return next((row for row in terms if row.is_current), terms[0] if terms else None)


def roster_counts(section_ids):
    if not section_ids:
        return {}
    rows = (
        StudentSection.objects.filter(section_id__in=section_ids, is_active=True)
        .exclude(student__user__account_status__in=HIDDEN)
        .values('section_id')
        .annotate(n=Count('id'))
    )
    return {row['section_id']: row['n'] for row in rows}


def grade_count_map(section_ids, year_ids):
    buckets = defaultdict(lambda: {'draft': 0, 'submitted': 0, 'approved': 0, 'released': 0, 'updated_at': None})
    if not section_ids or not year_ids:
        return buckets
    rows = (
        Grade.objects.filter(section_id__in=section_ids, school_year_id__in=year_ids)
        .values('section_id', 'subject_id', 'term_id', 'status')
        .annotate(n=Count('id'), updated_at=Max('updated_at'))
    )
    for row in rows:
        key = (row['section_id'], row['subject_id'], row['term_id'])
        bucket = buckets[key]
        if row['status'] in bucket:
            bucket[row['status']] = row['n']
        if row['updated_at'] and (bucket['updated_at'] is None or row['updated_at'] > bucket['updated_at']):
            bucket['updated_at'] = row['updated_at']
    return buckets


def offered_term_ids(assignments):
    """Term ids each duty has work in, in term order.

    A subject duty has the terms its subject runs in by the year's term plan. An advisory duty has
    every term in which at least one of the section's subjects runs. A term that already holds
    grades for the duty is always kept, so no recorded grade drops out of view.
    """
    duties = [row for row in assignments if row.section_id]
    section_ids = {row.section_id for row in duties}
    year_ids = {row.school_year_id for row in duties}
    terms_by_year = defaultdict(list)
    for term in Term.objects.filter(school_year_id__in=year_ids).order_by('number'):
        terms_by_year[term.school_year_id].append(term)
    plans = {year_id: TermPlan(year_id) for year_id in year_ids}
    programs = dict(Section.objects.filter(id__in=section_ids).values_list('id', 'program_id'))
    graded = defaultdict(set)
    for section_id, subject_id, term_id in (
        Grade.objects.filter(section_id__in=section_ids).values_list('section_id', 'subject_id', 'term_id').distinct()
    ):
        graded[(section_id, subject_id)].add(term_id)
    section_subjects = defaultdict(set)
    for section_id, subject_id in TeacherAssignment.objects.filter(
        section_id__in=section_ids,
        assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
        status=TeacherAssignment.Status.ACTIVE,
        subject__isnull=False,
    ).values_list('section_id', 'subject_id'):
        section_subjects[section_id].add(subject_id)

    def subject_terms(row, subject_id):
        plan = plans[row.school_year_id]
        program_id = programs.get(row.section_id)
        scheduled = {
            term.id
            for term in terms_by_year[row.school_year_id]
            if plan.runs_in(program_id, subject_id, term.number)
        }
        return scheduled | graded[(row.section_id, subject_id)]

    offered = {}
    for row in duties:
        if row.assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER and row.subject_id:
            ids = subject_terms(row, row.subject_id)
        elif row.assignment_type == TeacherAssignment.Type.ADVISER:
            ids = set().union(*(subject_terms(row, subject_id) for subject_id in section_subjects[row.section_id]))
        else:
            continue
        offered[row.id] = [term.id for term in terms_by_year[row.school_year_id] if term.id in ids]
    return offered


def assignment_progress(assignments, offered):
    """Encode progress per subject duty, for the terms the duty has work in (see offered_term_ids)."""
    encode_rows = [
        row
        for row in assignments
        if row.assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER and row.section_id and row.subject_id
    ]
    section_ids = {row.section_id for row in encode_rows}
    year_ids = {row.school_year_id for row in encode_rows}
    terms_by_year = defaultdict(list)
    for term in Term.objects.filter(school_year_id__in=year_ids).order_by('number'):
        terms_by_year[term.school_year_id].append(term)
    rosters = roster_counts(section_ids)
    grades = grade_count_map(section_ids, year_ids)
    payload = {}
    for row in encode_rows:
        terms = terms_by_year.get(row.school_year_id, [])
        current = _current_term(terms)
        roster = rosters.get(row.section_id, 0)
        term_rows = []
        for term in terms:
            if term.id not in offered.get(row.id, ()):
                continue
            counts = grades.get((row.section_id, row.subject_id, term.id), {})
            packed = pack_counts(
                roster,
                draft=counts.get('draft', 0),
                submitted=counts.get('submitted', 0),
                approved=counts.get('approved', 0),
                released=counts.get('released', 0),
                updated_at=counts.get('updated_at'),
            )
            packed['term_id'] = term.id
            packed['term'] = term.label
            packed['term_number'] = term.number
            term_rows.append(packed)
        current_payload = next((item for item in term_rows if current and item['term_id'] == current.id), None)
        payload[row.id] = {'current': current_payload, 'terms': term_rows}
    return payload


def duty_queue_rows(term):
    assignments = list(
        TeacherAssignment.objects.filter(
            school_year=term.school_year,
            status=TeacherAssignment.Status.ACTIVE,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            subject__isnull=False,
            section__isnull=False,
            section__archived_at__isnull=True,
        ).select_related('teacher', 'subject', 'section', 'section__program')
    )
    section_ids = {row.section_id for row in assignments}
    extra_ids = Grade.objects.filter(term=term).exclude(section_id=None).values_list('section_id', flat=True)
    section_ids.update(extra_ids)
    rosters = roster_counts(section_ids)
    grades = grade_count_map(section_ids, [term.school_year_id])
    plan = TermPlan(term.school_year_id)
    seen = set()
    rows = []
    for row in assignments:
        key = (row.section_id, row.subject_id)
        counts = grades.get((row.section_id, row.subject_id, term.id), {})
        if not counts and not plan.runs_in(row.section.program_id, row.subject_id, term.number):
            continue
        seen.add(key)
        packed = pack_counts(
            rosters.get(row.section_id, 0),
            draft=counts.get('draft', 0),
            submitted=counts.get('submitted', 0),
            approved=counts.get('approved', 0),
            released=counts.get('released', 0),
            updated_at=counts.get('updated_at'),
        )
        packed.update(
            {
                'teacher_id': row.teacher_id,
                'teacher': row.teacher.get_full_name() or row.teacher.email,
                'section_id': row.section_id,
                'section': _section_name(row.section),
                'subject_id': row.subject_id,
                'subject': row.subject.name,
            }
        )
        rows.append(packed)

    leftovers = (
        Grade.objects.filter(term=term)
        .values('teacher_id', 'teacher__first_name', 'teacher__last_name', 'teacher__email', 'section_id', 'subject_id', 'subject__name')
        .annotate(
            draft=Count('id', filter=Q(status=Grade.Status.DRAFT)),
            submitted=Count('id', filter=Q(status=Grade.Status.SUBMITTED)),
            approved=Count('id', filter=Q(status=Grade.Status.APPROVED)),
            released=Count('id', filter=Q(status=Grade.Status.RELEASED)),
            updated_at=Max('updated_at'),
        )
    )
    sections = {
        item.id: item
        for item in Section.objects.filter(id__in=[row['section_id'] for row in leftovers if row['section_id']]).select_related(
            'program'
        )
    }
    for row in leftovers:
        key = (row['section_id'], row['subject_id'])
        if key in seen or not row['section_id'] or not row['subject_id']:
            continue
        packed = pack_counts(
            rosters.get(row['section_id'], 0),
            draft=row['draft'],
            submitted=row['submitted'],
            approved=row['approved'],
            released=row['released'],
            updated_at=row['updated_at'],
        )
        first = row.get('teacher__first_name') or ''
        last = row.get('teacher__last_name') or ''
        teacher = ' '.join(part for part in (first, last) if part).strip() or row.get('teacher__email') or 'Unassigned teacher'
        packed.update(
            {
                'teacher_id': row['teacher_id'],
                'teacher': teacher,
                'section_id': row['section_id'],
                'section': _section_name(sections.get(row['section_id'])),
                'subject_id': row['subject_id'],
                'subject': row['subject__name'],
            }
        )
        rows.append(packed)
    rows.sort(key=lambda item: ((item.get('teacher') or '').lower(), item.get('section') or '', item.get('subject') or ''))
    return rows


def _section_name(section):
    if section is None:
        return 'Unassigned'
    from apps.school.labels import section_label

    return section_label(section) or section.name or 'Unassigned'
