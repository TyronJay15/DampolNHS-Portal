"""Student-facing college recommendation records: consent, the interest assessment, saved recommendations,
adviser records and training jobs.

The catalog, program profiles, configuration and trained models live in apps.ml (the engine). This app
reads the engine; the engine never imports this app.

Several tables need "only one open row at a time" (one active consent per kind, one assessment in
progress, one active instrument, one open training job). MySQL has no partial unique indexes, so each
uses a nullable unique *_marker column that holds a value only while the row is open.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.ml.models import RiasecType


class GuidanceConsent(models.Model):
    class Kind(models.TextChoices):
        ASSESSMENT = 'assessment', 'Take the assessment and receive recommendations'
        TRAINING = 'training', 'Use pseudonymous data to improve the recommender'

    class Party(models.TextChoices):
        STUDENT = 'student', 'Student (18 or older)'
        STUDENT_AND_GUARDIAN = 'student_and_guardian', 'Student, with parent or guardian consent'

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='guidance_consents')
    kind = models.CharField(max_length=12, choices=Kind.choices)
    party = models.CharField(max_length=24, choices=Party.choices)
    notice_version = models.CharField(max_length=16)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    given_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    active_marker = models.CharField(max_length=40, null=True, blank=True, unique=True)

    class Meta:
        db_table = 'guidance_consents'
        ordering = ['-given_at']
        indexes = [models.Index(fields=['student', 'kind'], name='guidance_consent_lookup')]


class InterestInstrument(models.Model):
    """One version of the interest assessment. Students answer only the active version."""

    ACTIVE = 'active'

    class Pilot(models.TextChoices):
        NOT_PILOTED = 'not_piloted', 'Not yet piloted'
        PILOTED = 'piloted', 'Piloted'

    code = models.SlugField(max_length=32)
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=160)
    source = models.CharField(max_length=255)
    source_url = models.URLField(blank=True)
    license_url = models.URLField(blank=True)
    attribution = models.TextField(help_text='Shown to students on the assessment screen, as the license requires.')
    license_confirmed_at = models.DateTimeField(null=True, blank=True)
    license_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    pilot_status = models.CharField(max_length=12, choices=Pilot.choices, default=Pilot.NOT_PILOTED)
    pilot_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    active_marker = models.CharField(max_length=8, null=True, blank=True, unique=True)

    class Meta:
        db_table = 'guidance_instruments'
        ordering = ['code', '-version']
        constraints = [
            models.UniqueConstraint(fields=['code', 'version'], name='one_instrument_version'),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'


class InterestQuestion(models.Model):
    instrument = models.ForeignKey(InterestInstrument, on_delete=models.CASCADE, related_name='questions')
    position = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=255)
    original_text = models.CharField(max_length=255)
    change_note = models.CharField(max_length=255, blank=True)
    riasec = models.CharField(max_length=1, choices=RiasecType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'guidance_questions'
        ordering = ['instrument', 'position']
        constraints = [
            models.UniqueConstraint(fields=['instrument', 'position'], name='one_question_per_position'),
        ]


class InterestAssessment(models.Model):
    """One attempt. Scores are written once, when the attempt is completed, and never recalculated."""

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='interest_assessments')
    instrument = models.ForeignKey(InterestInstrument, on_delete=models.PROTECT, related_name='assessments')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    scores = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    open_marker = models.CharField(max_length=24, null=True, blank=True, unique=True)

    class Meta:
        db_table = 'guidance_assessments'
        ordering = ['-started_at']
        indexes = [models.Index(fields=['student', 'status'], name='guidance_assessment_lookup')]


class InterestResponse(models.Model):
    assessment = models.ForeignKey(InterestAssessment, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(InterestQuestion, on_delete=models.PROTECT, related_name='+')
    value = models.PositiveSmallIntegerField()
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'guidance_responses'
        constraints = [
            models.UniqueConstraint(fields=['assessment', 'question'], name='one_response_per_question'),
            models.CheckConstraint(condition=Q(value__gte=1) & Q(value__lte=5), name='response_value_1_to_5'),
        ]


class RecommendationRun(models.Model):
    """One saved recommendation, with everything needed to explain and audit it later."""

    class Method(models.TextChoices):
        PROFILE_MATCHING = 'profile_matching', 'Profile matching'
        HYBRID_ML = 'hybrid_ml', 'Machine learning with profile matching'

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='recommendation_runs')
    method = models.CharField(max_length=20, choices=Method.choices)
    family_model = models.ForeignKey('ml.ModelRun', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    program_model = models.ForeignKey('ml.ModelRun', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    assessment = models.ForeignKey(InterestAssessment, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    instrument_version = models.PositiveIntegerField(null=True, blank=True)
    config = models.ForeignKey('ml.RecommenderConfig', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    feature_schema = models.CharField(max_length=16)
    catalog_version = models.CharField(max_length=16)
    features = models.JSONField(default=dict)
    fingerprint = models.CharField(max_length=64, db_index=True)
    ready = models.BooleanField(default=False)
    not_ready_reason = models.CharField(max_length=32, blank=True)
    fallback_reason = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'guidance_recommendation_runs'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['student', '-created_at'], name='guidance_run_latest')]


class RecommendationItem(models.Model):
    class Tier(models.TextChoices):
        PRIMARY = 'primary', 'Primary'
        ADDITIONAL = 'additional', 'Explore more'

    class Label(models.TextChoices):
        STRONG = 'strong', 'Strong Match'
        GOOD = 'good', 'Good Match'
        POSSIBLE = 'possible', 'Possible Match'
        LIMITED = 'limited', 'Limited Evidence'

    run = models.ForeignKey(RecommendationRun, on_delete=models.CASCADE, related_name='items')
    college_program = models.ForeignKey('ml.CollegeProgram', on_delete=models.PROTECT, related_name='+')
    rank = models.PositiveSmallIntegerField()
    tier = models.CharField(max_length=12, choices=Tier.choices)
    label = models.CharField(max_length=12, choices=Label.choices)
    evidence = models.JSONField(default=dict)

    class Meta:
        db_table = 'guidance_recommendation_items'
        ordering = ['run', 'rank']
        constraints = [
            models.UniqueConstraint(fields=['run', 'rank'], name='one_item_per_rank'),
            models.UniqueConstraint(fields=['run', 'college_program'], name='one_item_per_program'),
            models.CheckConstraint(condition=Q(rank__gte=1), name='item_rank_from_one'),
        ]


class AdviserNote(models.Model):
    """Append-only note by the student's adviser. Not shown to the student."""

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='adviser_notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guidance_adviser_notes'
        ordering = ['-created_at']


class AdviserRecommendation(models.Model):
    """The adviser's own suggestion. A separate record; it never changes a system recommendation."""

    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='adviser_recommendations',
    )
    adviser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    college_program = models.ForeignKey('ml.CollegeProgram', on_delete=models.PROTECT, related_name='+')
    reason = models.TextField()
    run = models.ForeignKey(RecommendationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guidance_adviser_recommendations'
        ordering = ['-created_at']

