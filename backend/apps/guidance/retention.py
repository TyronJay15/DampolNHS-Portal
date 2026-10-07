"""Delete old guidance answers after graduates leave the keep window.

Raw assessments and saved recommendations are kept while the student is in the current school year,
and for GUIDANCE_KEEP_DAYS after they leave.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Max
from django.utils import timezone

from apps.guidance.models import InterestAssessment, RecommendationRun
from apps.people.models import StudentSection
from apps.school.models import SchoolYear


def prune_guidance():
    """Delete old assessments and saved runs for graduates past the keep window."""
    keep_days = settings.GUIDANCE_KEEP_DAYS
    current = SchoolYear.objects.filter(is_current=True).first()
    enrolled = set()
    if current:
        enrolled = set(
            StudentSection.objects.filter(school_year=current, is_active=True).values_list('student_id', flat=True)
        )
    latest_year = dict(
        StudentSection.objects.values('student_id').annotate(last=Max('school_year__ends_on')).values_list('student_id', 'last')
    )
    cutoff = timezone.localdate() - timedelta(days=keep_days)
    stale = []
    student_ids = set(InterestAssessment.objects.values_list('student_id', flat=True)) | set(
        RecommendationRun.objects.values_list('student_id', flat=True)
    )
    for student_id in student_ids:
        if student_id in enrolled:
            continue
        ended = latest_year.get(student_id)
        if ended is None or ended > cutoff:
            continue
        stale.append(student_id)
    if not stale:
        return {'assessments': 0, 'recommendations': 0}
    assessments = InterestAssessment.objects.filter(student_id__in=stale).delete()[0]
    recommendations = RecommendationRun.objects.filter(student_id__in=stale).delete()[0]
    return {'assessments': assessments, 'recommendations': recommendations}
