from django.db import models


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

    class Meta:
        db_table = 'ml_cluster_snapshot'
        unique_together = ('school_year', 'cluster_code')
        ordering = ['school_year_id', 'cluster_code']


class ModelRun(models.Model):
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

    class Meta:
        db_table = 'ml_model_run'
        ordering = ['-trained_at']


class CollegeProgram(models.Model):
    """A college course the recommender can suggest. Curated profile, not learned."""

    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    shs_programs = models.ManyToManyField(
        'school.Program',
        blank=True,
        related_name='college_programs',
        help_text='SHS programs that lead naturally to this course.',
    )

    class Meta:
        db_table = 'ml_college_programs'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.name


class CollegeProgramSkill(models.Model):
    """Expected grade level in one skill domain. minimum, when set, is a hard floor."""

    college_program = models.ForeignKey(CollegeProgram, on_delete=models.CASCADE, related_name='skills')
    domain = models.ForeignKey('school.SkillDomain', on_delete=models.PROTECT, related_name='college_skills')
    level = models.DecimalField(max_digits=5, decimal_places=2)
    minimum = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'ml_college_program_skills'
        ordering = ['college_program', 'domain__sort_order']
        constraints = [
            models.UniqueConstraint(fields=['college_program', 'domain'], name='one_skill_row_per_domain'),
        ]


class CollegeOutcome(models.Model):
    """The college course a graduate actually entered. Labeled data for a future trained model."""

    student = models.OneToOneField(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='college_outcome',
    )
    college_program = models.ForeignKey(CollegeProgram, on_delete=models.PROTECT, related_name='outcomes')
    school_year = models.ForeignKey('school.SchoolYear', on_delete=models.PROTECT, related_name='college_outcomes')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ml_college_outcomes'
        ordering = ['-recorded_at']
