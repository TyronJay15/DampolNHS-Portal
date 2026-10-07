"""Taking the interest assessment: start, answer one question at a time, complete.

Answers are saved as they are given, so a student can stop and continue later. A type score is the mean
of its answers on the 1 to 5 scale, written once when the attempt is completed and never recalculated.
"""

from collections import defaultdict

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.guidance.models import GuidanceConsent, InterestAssessment, InterestQuestion, InterestResponse
from apps.guidance.selectors import active_consent, active_instrument, open_attempt
from apps.ml.features import RIASEC_ORDER

LOWEST = 1
HIGHEST = 5


def _require_consent(student):
    if active_consent(student, GuidanceConsent.Kind.ASSESSMENT) is None:
        raise ValidationError({'detail': 'Agree to the privacy notice before taking the assessment.'})


def questions(instrument):
    return list(InterestQuestion.objects.filter(instrument=instrument, is_active=True).order_by('position'))


def start(student):
    _require_consent(student)
    instrument = active_instrument()
    if instrument is None:
        raise ValidationError({'detail': 'The interest assessment is not open yet. Your adviser will tell you when it is.'})
    attempt = open_attempt(student)
    if attempt and attempt.instrument_id == instrument.pk:
        return attempt
    with transaction.atomic():
        if attempt:
            # The school switched to a new instrument version; answers to the old one cannot be mixed in.
            attempt.delete()
        try:
            return InterestAssessment.objects.create(
                student=student,
                instrument=instrument,
                open_marker=str(student.pk),
            )
        except IntegrityError:
            return open_attempt(student)


def answer(student, question_id, value):
    _require_consent(student)
    if isinstance(value, bool) or not isinstance(value, int) or not LOWEST <= value <= HIGHEST:
        raise ValidationError({'value': f'Choose an answer from {LOWEST} to {HIGHEST}.'})
    attempt = open_attempt(student)
    if attempt is None:
        raise ValidationError({'detail': 'Start the assessment first.'})
    question = InterestQuestion.objects.filter(pk=question_id, instrument=attempt.instrument, is_active=True).first()
    if question is None:
        raise NotFound('That question is not part of your assessment.')
    InterestResponse.objects.update_or_create(assessment=attempt, question=question, defaults={'value': value})
    return attempt


def scores_from(responses):
    """RIASEC letter -> mean answer, rounded to two decimals."""
    by_type = defaultdict(list)
    for response in responses:
        by_type[response.question.riasec].append(response.value)
    return {letter: round(sum(by_type[letter]) / len(by_type[letter]), 2) for letter in RIASEC_ORDER}


def complete(student):
    _require_consent(student)
    attempt = open_attempt(student)
    if attempt is None:
        raise ValidationError({'detail': 'There is no assessment in progress.'})
    asked = questions(attempt.instrument)
    if set(RIASEC_ORDER) - {question.riasec for question in asked}:
        raise ValidationError({'detail': 'This assessment version does not cover all six interest types. Tell the school administrator.'})
    responses = list(
        InterestResponse.objects.filter(assessment=attempt, question__in=asked).select_related('question')
    )
    missing = len(asked) - len(responses)
    if missing:
        raise ValidationError({'detail': f'{missing} question{"s are" if missing != 1 else " is"} still unanswered.'})
    attempt.scores = scores_from(responses)
    attempt.status = InterestAssessment.Status.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.open_marker = None
    attempt.save(update_fields=['scores', 'status', 'completed_at', 'open_marker'])
    return attempt


def progress(attempt):
    if attempt is None:
        return None
    answers = dict(InterestResponse.objects.filter(assessment=attempt).values_list('question_id', 'value'))
    return {'id': attempt.pk, 'instrument_version': attempt.instrument.version, 'answers': answers}
