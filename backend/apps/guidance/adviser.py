"""What an adviser can see and record for the students of their own section."""

from django.db import transaction
from django.db.models import Max, Prefetch
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.lifecycle import HIDDEN
from apps.audit import services as audit
from apps.guidance.models import (
    AdviserNote,
    AdviserRecommendation,
    GuidanceConsent,
    InterestAssessment,
    RecommendationItem,
    RecommendationRun,
)
from apps.ml.models import CollegeOutcome, CollegeProgram
from apps.people.models import StudentSection

NOTE_LIMIT = 2000
REASON_LIMIT = 1000


def roster(assignment):
    rows = list(
        StudentSection.objects.filter(section=assignment.section, school_year=assignment.school_year, is_active=True)
        .exclude(student__user__account_status__in=HIDDEN)
        .select_related('student__user')
        .order_by('student__user__last_name', 'student__user__first_name')
    )
    ids = [row.student_id for row in rows]
    consenting = set(
        GuidanceConsent.objects.filter(
            student_id__in=ids,
            kind=GuidanceConsent.Kind.ASSESSMENT,
            withdrawn_at__isnull=True,
        ).values_list('student_id', flat=True)
    )
    statuses = {}
    for row in InterestAssessment.objects.filter(student_id__in=ids).order_by('started_at'):
        statuses[row.student_id] = row.status
    latest_ids = (
        RecommendationRun.objects.filter(student_id__in=ids)
        .values('student_id')
        .annotate(last=Max('id'))
        .values_list('last', flat=True)
    )
    top_items = Prefetch('items', queryset=RecommendationItem.objects.filter(rank=1).select_related('college_program'))
    latest = {run.student_id: run for run in RecommendationRun.objects.filter(pk__in=list(latest_ids)).prefetch_related(top_items)}
    outcomes = {row.student_id: row for row in CollegeOutcome.objects.filter(student_id__in=ids).select_related('college_program')}
    students = []
    for row in rows:
        run = latest.get(row.student_id)
        top = next(iter(run.items.all()), None) if run else None
        outcome = outcomes.get(row.student_id)
        students.append(
            {
                'student_id': row.student_id,
                'name': row.student.user.get_full_name(),
                'consent': row.student_id in consenting,
                'assessment': statuses.get(row.student_id, 'not_started'),
                'recommendation': (
                    {'program': top.college_program.name, 'label': top.label, 'method': run.method} if top else None
                ),
                'outcome': (
                    {'program': outcome.college_program.name, 'status': outcome.status} if outcome else None
                ),
            }
        )
    return students


def notes(student):
    return [
        {
            'id': note.pk,
            'body': note.body,
            'author': note.author.get_full_name() if note.author else 'Former staff',
            'created_at': note.created_at,
        }
        for note in AdviserNote.objects.filter(student=student).select_related('author')
    ]


def recommendations(student):
    return [
        {
            'id': row.pk,
            'program': {'code': row.college_program.code, 'name': row.college_program.name},
            'reason': row.reason,
            'adviser': row.adviser.get_full_name() if row.adviser else 'Former staff',
            'run': row.run_id,
            'created_at': row.created_at,
        }
        for row in AdviserRecommendation.objects.filter(student=student).select_related('college_program', 'adviser')
    ]


def add_note(student, body, *, user):
    body = str(body or '').strip()
    if not body:
        raise ValidationError({'body': 'Write the note first.'})
    if len(body) > NOTE_LIMIT:
        raise ValidationError({'body': f'Keep notes under {NOTE_LIMIT} characters.'})
    note = AdviserNote.objects.create(student=student, author=user, body=body)
    audit.record(
        user=user,
        action='adviser_note_added',
        summary='Adviser note added',
        target_type='StudentProfile',
        target_id=student.pk,
    )
    return note


def _active_program(code):
    program = CollegeProgram.objects.filter(code=str(code or ''), is_active=True).first()
    if program is None:
        raise ValidationError({'program': 'Choose an active college program.'})
    return program


def add_recommendation(student, data, *, user, run):
    program = _active_program(data.get('program'))
    reason = str(data.get('reason') or '').strip()
    if not reason:
        raise ValidationError({'reason': 'Explain the recommendation so it can be understood later.'})
    if len(reason) > REASON_LIMIT:
        raise ValidationError({'reason': f'Keep the reason under {REASON_LIMIT} characters.'})
    row = AdviserRecommendation.objects.create(student=student, adviser=user, college_program=program, reason=reason, run=run)
    audit.record(
        user=user,
        action='adviser_recommendation_added',
        summary=f'Adviser recommendation added: {program.name}',
        target_type='StudentProfile',
        target_id=student.pk,
        details={'program': program.code, 'run': run.pk if run else None},
    )
    return row


def record_outcome(student, data, *, user, assignment):
    """The adviser records the program a graduate entered. A validated outcome can no longer be changed."""
    program = _active_program(data.get('program'))
    with transaction.atomic():
        outcome = CollegeOutcome.objects.select_for_update().filter(student=student).first()
        if outcome and outcome.status == CollegeOutcome.Status.VALIDATED:
            raise ValidationError({'detail': 'This outcome was already validated and can no longer be changed.'})
        if outcome is None:
            outcome = CollegeOutcome.objects.create(
                student=student,
                college_program=program,
                school_year=assignment.school_year,
                recorded_by=user,
            )
        else:
            outcome.college_program = program
            outcome.recorded_by = user
            outcome.save(update_fields=['college_program', 'recorded_by'])
    audit.record(
        user=user,
        action='college_outcome_recorded',
        summary=f'College outcome recorded: {program.name}',
        target_type='StudentProfile',
        target_id=student.pk,
        details={'program': program.code},
    )
    return outcome


def validate_outcome(outcome, *, user):
    if outcome.status == CollegeOutcome.Status.VALIDATED:
        raise ValidationError({'detail': 'This outcome is already validated.'})
    if outcome.recorded_by_id == user.pk:
        raise ValidationError({'detail': 'A second person must validate an outcome; you recorded this one.'})
    outcome.status = CollegeOutcome.Status.VALIDATED
    outcome.validated_by = user
    outcome.validated_at = timezone.now()
    outcome.save(update_fields=['status', 'validated_by', 'validated_at'])
    audit.record(
        user=user,
        action='college_outcome_validated',
        summary=f'College outcome validated: {outcome.college_program.name}',
        target_type='CollegeOutcome',
        target_id=outcome.pk,
    )
    return outcome


def outcome_payload(outcome):
    if outcome is None:
        return None
    return {
        'id': outcome.pk,
        'program': {'code': outcome.college_program.code, 'name': outcome.college_program.name},
        'status': outcome.status,
        'recorded_at': outcome.recorded_at,
    }
