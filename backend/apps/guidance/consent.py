"""The only place guidance consent changes, and the privacy notice students agree to.

ASSESSMENT consent is required to take the survey and receive the live ML recommendation. TRAINING
consent remains in the database for older records but is no longer offered in the student screens.
For a student under 18, or whose birthdate is unknown, the student must confirm that a parent or
guardian agreed. Withdrawing the assessment consent also withdraws training consent and deletes the
assessment answers and saved recommendations, because their basis is gone.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.guidance.models import GuidanceConsent, InterestAssessment, RecommendationRun
from apps.guidance.selectors import active_consent

ADULT_AGE = 18
NOTICE_VERSION = '2026-10-06'
NOTICE = {
    'version': NOTICE_VERSION,
    'sections': [
        {
            'title': 'What is used',
            'body': 'Your released Grade 11 and 12 grades, your SHS strand and your answers to the 30-question '
            'interest assessment. Your name, LRN, contact details and address are never used to rank programs.',
        },
        {
            'title': 'Why',
            'body': 'To suggest college degree programs that align with your strengths and interests. The result is an '
            'ML recommendation: a starting point for planning, not a decision and not an admission requirement. It is '
            'not a model trained on past graduates.',
        },
        {
            'title': 'Who can see it',
            'body': 'You and your own class adviser. School administrators see totals only.',
        },
        {
            'title': 'Withdrawing',
            'body': 'You can withdraw at any time. Your answers and saved recommendations are then deleted. You can '
            'agree again later if you want a full match list.',
        },
        {
            'title': 'How long',
            'body': 'Your answers and recommendations are kept while you are enrolled and for up to one year after '
            'graduation, as decided by the school and its Data Protection Officer.',
        },
    ],
}


def is_minor(student, today=None):
    """True under 18. An unknown birthdate counts as a minor, so a guardian's consent is always confirmed."""
    birthdate = student.birthdate
    if birthdate is None:
        return True
    today = today or timezone.localdate()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age < ADULT_AGE


def _marker(student, kind):
    return f'{student.pk}:{kind}'


def give(student, kind, *, guardian_confirmed, notice_version, user):
    if kind not in GuidanceConsent.Kind.values:
        raise ValidationError({'kind': 'Choose a valid consent.'})
    if notice_version != NOTICE_VERSION:
        raise ValidationError({'notice_version': 'The privacy notice has changed. Read it again before agreeing.'})
    if kind == GuidanceConsent.Kind.TRAINING and active_consent(student, GuidanceConsent.Kind.ASSESSMENT) is None:
        raise ValidationError({'kind': 'Agree to the assessment first.'})
    minor = is_minor(student)
    if minor and not guardian_confirmed:
        raise ValidationError({'guardian_confirmed': 'A parent or guardian must agree first, because you are under 18.'})
    existing = active_consent(student, kind)
    if existing:
        return existing
    party = GuidanceConsent.Party.STUDENT_AND_GUARDIAN if minor else GuidanceConsent.Party.STUDENT
    try:
        consent = GuidanceConsent.objects.create(
            student=student,
            kind=kind,
            party=party,
            notice_version=notice_version,
            recorded_by=user,
            active_marker=_marker(student, kind),
        )
    except IntegrityError:
        return active_consent(student, kind)
    audit.record(
        user=user,
        action='guidance_consent_given',
        summary=f'Recommendation consent given: {GuidanceConsent.Kind(kind).label}',
        target_type='StudentProfile',
        target_id=student.pk,
        details={'kind': kind, 'party': party, 'notice_version': notice_version},
    )
    return consent


def withdraw(student, kind, *, user):
    consent = active_consent(student, kind)
    if consent is None:
        raise ValidationError({'kind': 'There is no active consent to withdraw.'})
    with transaction.atomic():
        kinds = [kind]
        if kind == GuidanceConsent.Kind.ASSESSMENT:
            kinds.append(GuidanceConsent.Kind.TRAINING)
        GuidanceConsent.objects.filter(student=student, kind__in=kinds, withdrawn_at__isnull=True).update(
            withdrawn_at=timezone.now(),
            active_marker=None,
        )
        if kind == GuidanceConsent.Kind.ASSESSMENT:
            _delete_answers(student)
    audit.record(
        user=user,
        action='guidance_consent_withdrawn',
        summary=f'Recommendation consent withdrawn: {GuidanceConsent.Kind(kind).label}',
        target_type='StudentProfile',
        target_id=student.pk,
        details={'kinds': kinds},
    )


def delete_data(student, *, user):
    """Delete the student's assessment answers and saved recommendations. Consent records stay as proof."""
    with transaction.atomic():
        counts = _delete_answers(student)
    audit.record(
        user=user,
        action='guidance_data_deleted',
        summary='Recommendation answers and saved recommendations deleted at the student\'s request',
        target_type='StudentProfile',
        target_id=student.pk,
        details=counts,
    )


def _delete_answers(student):
    runs = RecommendationRun.objects.filter(student=student)
    assessments = InterestAssessment.objects.filter(student=student)
    counts = {
        'recommendations': runs.count(),
        'assessments': assessments.count(),
    }
    runs.delete()
    assessments.delete()
    return counts


def consent_state(student):
    assessment = active_consent(student, GuidanceConsent.Kind.ASSESSMENT)
    training = active_consent(student, GuidanceConsent.Kind.TRAINING)
    return {
        'notice': NOTICE,
        'minor': is_minor(student),
        'assessment': _consent_dict(assessment),
        'training': _consent_dict(training),
    }


def _consent_dict(consent):
    if consent is None:
        return None
    return {'given_at': consent.given_at, 'party': consent.party, 'notice_version': consent.notice_version}
