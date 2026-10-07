"""Read-only queries shared by the guidance services and views. Writes live in the service modules."""

from apps.guidance.models import GuidanceConsent, InterestAssessment, InterestInstrument, RecommendationRun
from apps.people.models import StudentSection
from apps.people.placement import approved_registration, student_program


def active_instrument():
    return InterestInstrument.objects.filter(active_marker=InterestInstrument.ACTIVE).first()


def active_consent(student, kind):
    return GuidanceConsent.objects.filter(student=student, kind=kind, withdrawn_at__isnull=True).first()


def open_attempt(student):
    return (
        InterestAssessment.objects.filter(student=student, status=InterestAssessment.Status.IN_PROGRESS)
        .select_related('instrument')
        .first()
    )


def latest_completed(student):
    return (
        InterestAssessment.objects.filter(student=student, status=InterestAssessment.Status.COMPLETED)
        .select_related('instrument')
        .order_by('-completed_at', '-id')
        .first()
    )


def assessment_consenting(student_ids):
    return set(
        GuidanceConsent.objects.filter(
            student_id__in=student_ids,
            kind=GuidanceConsent.Kind.ASSESSMENT,
            withdrawn_at__isnull=True,
        ).values_list('student_id', flat=True)
    )


def interest_scores(student_ids):
    """Student id -> scores of the latest completed assessment, for students who still consent to it."""
    consenting = assessment_consenting(student_ids)
    latest = {}
    rows = InterestAssessment.objects.filter(
        student_id__in=consenting,
        status=InterestAssessment.Status.COMPLETED,
    ).order_by('student_id', 'completed_at', 'id')
    for row in rows:
        latest[row.student_id] = row.scores
    return latest


def placement(student):
    return (
        StudentSection.objects.filter(student=student, is_active=True)
        .select_related('section', 'section__program', 'school_year')
        .order_by('-school_year__label')
        .first()
    )


def shs_program(student):
    """The student's SHS program: the active section's program, else the approved registration's."""
    return student_program(student, approved_registration(student.user), placement(student))


def latest_run(student):
    return (
        RecommendationRun.objects.filter(student=student)
        .select_related('family_model', 'program_model', 'config')
        .prefetch_related('items__college_program__family')
        .first()
    )
