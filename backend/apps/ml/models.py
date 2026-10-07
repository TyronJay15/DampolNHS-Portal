from django.conf import settings
from django.db import models
from django.db.models import F, Q


class ChatQuestion(models.Model):
    question = models.CharField(max_length=400)
    topic = models.CharField(max_length=32, db_index=True)
    confidence = models.FloatField(default=0)
    source = models.CharField(max_length=16, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ml_chat_question'
        ordering = ['-created_at']


class ClusterSnapshot(models.Model):
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.CASCADE,
        related_name='cluster_snapshots',
    )
    cluster_code = models.CharField(max_length=16)
    program = models.ForeignKey(
        'school.Program',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cluster_snapshots',
    )
    curriculum = models.ForeignKey(
        'school.Curriculum',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cluster_snapshots',
    )
    applied_count = models.PositiveIntegerField(default=0)
    approved_count = models.PositiveIntegerField(default=0)
    is_synthetic = models.BooleanField(
        default=False,
        help_text='Invented history written by seed_demo_forecast in a demo database. Never true for real years.',
    )

    class Meta:
        db_table = 'ml_cluster_snapshot'
        unique_together = ('school_year', 'cluster_code')
        ordering = ['school_year_id', 'cluster_code']


class ModelRun(models.Model):
    """One trained model version. Forecast and chatbot intent runs use this table."""

    class Status(models.TextChoices):
        TRAINED = 'trained', 'Trained'
        EVALUATED = 'evaluated', 'Evaluated'
        CANDIDATE = 'candidate', 'Candidate'
        ACTIVE = 'active', 'Active'
        REJECTED = 'rejected', 'Rejected'
        ARCHIVED = 'archived', 'Archived'

    name = models.CharField(max_length=32, db_index=True)
    algorithm = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    n_train = models.PositiveIntegerField(default=0)
    n_test = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(default=dict)
    artifact = models.JSONField(default=dict)
    feature_schema = models.JSONField(default=dict, blank=True)
    curriculum_scope = models.JSONField(default=list, blank=True)
    dataset = models.JSONField(default=dict, blank=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, null=True, blank=True, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    # Holds the run name while the run is ACTIVE and NULL otherwise. MySQL has no partial unique
    # indexes, so this unique column is what allows only one active model per role.
    active_marker = models.CharField(max_length=32, null=True, blank=True, unique=True)

    class Meta:
        db_table = 'ml_model_run'
        ordering = ['-trained_at']


class RiasecType(models.TextChoices):
    """Holland's six interest types, as measured by the interest assessment."""

    REALISTIC = 'R', 'Realistic'
    INVESTIGATIVE = 'I', 'Investigative'
    ARTISTIC = 'A', 'Artistic'
    SOCIAL = 'S', 'Social'
    ENTERPRISING = 'E', 'Enterprising'
    CONVENTIONAL = 'C', 'Conventional'


class ProgramFamily(models.Model):
    """A broad group of college programs. Families are data: adding or renaming one needs no code change."""

    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'ml_program_families'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class FamilyInterestMap(models.Model):
    """The interest types that describe a family. Sets only the interest-alignment label, never a model input."""

    family = models.ForeignKey(ProgramFamily, on_delete=models.CASCADE, related_name='interest_types')
    riasec = models.CharField(max_length=1, choices=RiasecType.choices)

    class Meta:
        db_table = 'ml_family_interest_map'
        ordering = ['family', 'riasec']
        constraints = [
            models.UniqueConstraint(fields=['family', 'riasec'], name='one_interest_type_per_family'),
        ]


class CollegeProgram(models.Model):
    """A college degree program the recommender can suggest. Sourced and verified, never invented."""

    class Verification(models.TextChoices):
        UNVERIFIED = 'unverified', 'Unverified'
        VERIFIED = 'verified', 'Verified'

    class ProfileStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft, not yet validated'
        VALIDATED = 'validated', 'Validated by experts'

    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=160, help_text='Official program name.')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    shs_programs = models.ManyToManyField(
        'school.Program',
        blank=True,
        related_name='college_programs',
        help_text='SHS programs that lead naturally to this course.',
    )
    family = models.ForeignKey(
        ProgramFamily,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='programs',
    )
    abbreviation = models.CharField(max_length=24, blank=True)
    description = models.TextField(blank=True)
    career_overview = models.TextField(blank=True)
    source = models.CharField(max_length=255, blank=True, help_text='Authoritative source, such as a CHED issuance.')
    source_url = models.URLField(blank=True)
    verified_on = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    verification_status = models.CharField(
        max_length=12,
        choices=Verification.choices,
        default=Verification.UNVERIFIED,
        db_index=True,
    )
    profile_status = models.CharField(max_length=12, choices=ProfileStatus.choices, default=ProfileStatus.DRAFT)
    profile_version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'ml_college_programs'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.name


class CollegeProgramSkill(models.Model):
    """Expected grade level in one skill domain, with an optional benchmark.

    A benchmark is guidance and never removes a program. Only a minimum of kind OFFICIAL, with its
    authoritative source, may be shown as a requirement.
    """

    class MinimumKind(models.TextChoices):
        BENCHMARK = 'benchmark', 'Profile benchmark'
        OFFICIAL = 'official', 'Official requirement'

    college_program = models.ForeignKey(CollegeProgram, on_delete=models.CASCADE, related_name='skills')
    domain = models.ForeignKey('school.SkillDomain', on_delete=models.PROTECT, related_name='college_skills')
    level = models.DecimalField(max_digits=5, decimal_places=2)
    minimum = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    minimum_kind = models.CharField(max_length=12, choices=MinimumKind.choices, default=MinimumKind.BENCHMARK)
    requirement_source = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'ml_college_program_skills'
        ordering = ['college_program', 'domain__sort_order']
        constraints = [
            models.UniqueConstraint(fields=['college_program', 'domain'], name='one_skill_row_per_domain'),
            models.CheckConstraint(
                condition=Q(level__gte=0) & Q(level__lte=100),
                name='college_skill_level_in_range',
            ),
            models.CheckConstraint(
                condition=Q(minimum__isnull=True) | (Q(minimum__gte=0) & Q(minimum__lte=100)),
                name='college_skill_minimum_in_range',
            ),
            models.CheckConstraint(
                condition=~Q(minimum_kind='official') | (Q(minimum__isnull=False) & ~Q(requirement_source='')),
                name='official_requirement_has_source',
            ),
        ]


class ProgramProfileSnapshot(models.Model):
    """A copy of a program profile each time it changes, so every version stays traceable."""

    college_program = models.ForeignKey(CollegeProgram, on_delete=models.CASCADE, related_name='profile_snapshots')
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=CollegeProgram.ProfileStatus.choices)
    rows = models.JSONField(default=list)
    source = models.CharField(max_length=255, blank=True)
    validators = models.JSONField(default=list, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ml_program_profile_snapshots'
        ordering = ['college_program', '-version']
        constraints = [
            models.UniqueConstraint(fields=['college_program', 'version'], name='one_snapshot_per_profile_version'),
        ]


class ProgramSkillRating(models.Model):
    """One expert's rating of a program's skill level. Validation input, never a training label."""

    college_program = models.ForeignKey(CollegeProgram, on_delete=models.CASCADE, related_name='ratings')
    domain = models.ForeignKey('school.SkillDomain', on_delete=models.PROTECT, related_name='+')
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    round = models.PositiveIntegerField(help_text='The profile version these ratings will produce.')
    level = models.DecimalField(max_digits=5, decimal_places=2)
    benchmark = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ml_program_skill_ratings'
        ordering = ['college_program', 'round', 'domain__sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['college_program', 'domain', 'rater', 'round'],
                name='one_rating_per_rater_round',
            ),
            models.CheckConstraint(condition=Q(level__gte=0) & Q(level__lte=100), name='rating_level_in_range'),
            models.CheckConstraint(
                condition=Q(benchmark__isnull=True) | (Q(benchmark__gte=0) & Q(benchmark__lte=100)),
                name='rating_benchmark_in_range',
            ),
        ]


class RecommenderConfig(models.Model):
    """A version of the values that change recommendation results. Exactly one is active."""

    version = models.PositiveIntegerField(unique=True)
    values = models.JSONField()
    note = models.CharField(max_length=255, blank=True)
    is_approved = models.BooleanField(
        default=False,
        help_text='True once the school panel has approved these values; until then they are provisional.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    # 'active' on the one active version, NULL on the rest (a unique column instead of a partial index).
    active_marker = models.CharField(max_length=8, null=True, blank=True, unique=True)

    class Meta:
        db_table = 'ml_recommender_configs'
        ordering = ['-version']


class CollegeOutcome(models.Model):
    """The college program a graduate actually entered. A training label only once validated."""

    class Status(models.TextChoices):
        RECORDED = 'recorded', 'Recorded'
        VALIDATED = 'validated', 'Validated'

    student = models.OneToOneField(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='college_outcome',
    )
    college_program = models.ForeignKey(CollegeProgram, on_delete=models.PROTECT, related_name='outcomes')
    school_year = models.ForeignKey('school.SchoolYear', on_delete=models.PROTECT, related_name='college_outcomes')
    recorded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECORDED, db_index=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    is_synthetic = models.BooleanField(
        default=False,
        help_text='Invented by a demo seed. Production training never reads synthetic outcomes.',
    )

    class Meta:
        db_table = 'ml_college_outcomes'
        ordering = ['-recorded_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(validated_by__isnull=True) | Q(recorded_by__isnull=True) | ~Q(validated_by=F('recorded_by')),
                name='outcome_validated_by_second_person',
            ),
        ]
