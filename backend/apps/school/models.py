from django.core.exceptions import ValidationError
from django.db import models


class SchoolYear(models.Model):
    label = models.CharField(max_length=9, unique=True, help_text='e.g. 2025-2026')
    is_current = models.BooleanField(default=False, db_index=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'school_years'
        ordering = ['-label']

    def save(self, *args, **kwargs):
        if self.archived_at:
            self.is_current = False
        if self.is_current:
            SchoolYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class Term(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'

    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='terms')
    number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPCOMING)
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    encode_opens_at = models.DateTimeField(null=True, blank=True)
    encode_closes_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'school_terms'
        ordering = ['school_year', 'number']
        constraints = [
            models.UniqueConstraint(fields=['school_year', 'number'], name='unique_term_per_year'),
            models.CheckConstraint(
                condition=models.Q(number__gte=1) & models.Q(number__lte=3),
                name='term_number_1_to_3',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = f'Term {self.number}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.label} ({self.school_year.label})'


class Curriculum(models.Model):
    """A curriculum version, e.g. K to 12 SHS or Strengthened SHS. Old versions stay for history."""

    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'school_curricula'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.name


class SkillDomain(models.Model):
    """Academic domain a subject's grade counts toward. Active domains, in order, are the ML feature schema."""

    key = models.SlugField(max_length=32, unique=True)
    label = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'school_skill_domains'
        ordering = ['sort_order', 'key']

    def __str__(self):
        return self.label


class Program(models.Model):
    class GradeLevel(models.TextChoices):
        GRADE_11 = 'Grade 11', 'Grade 11'
        GRADE_12 = 'Grade 12', 'Grade 12'

    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    track = models.CharField(max_length=64, blank=True)
    grade_level = models.CharField(max_length=16, blank=True, choices=GradeLevel.choices)
    pathways = models.JSONField(default=list, blank=True)
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='programs',
    )
    continues_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='continued_from',
        help_text='Grade 12 program this Grade 11 program leads to.',
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'school_programs'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.code

    def check_grade(self, grade_level, field='grade_level'):
        """Refuse a record whose grade level does not match this program's grade level."""
        if self.grade_level and grade_level and grade_level != self.grade_level:
            raise ValidationError({field: f'{self.code} is a {self.grade_level} program.'})


class SchoolYearCurriculum(models.Model):
    """Which curriculum a grade level followed in a school year. Keeps transition years historically correct."""

    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='curricula')
    grade_level = models.CharField(max_length=16, choices=Program.GradeLevel.choices)
    curriculum = models.ForeignKey(Curriculum, on_delete=models.PROTECT, related_name='school_years')

    class Meta:
        db_table = 'school_year_curricula'
        ordering = ['school_year', 'grade_level']
        constraints = [
            models.UniqueConstraint(fields=['school_year', 'grade_level'], name='one_curriculum_per_year_grade'),
        ]

    def __str__(self):
        return f'{self.school_year.label} {self.grade_level}: {self.curriculum.code}'


class Subject(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    skill_domain = models.ForeignKey(
        SkillDomain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subjects',
    )
    matching_excluded = models.BooleanField(
        default=False,
        help_text='Deliberately left out of college matching (e.g. PE). '
        'A subject with no skill domain and this unticked is reported as unmapped.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'school_subjects'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProgramSubject(models.Model):
    class Kind(models.TextChoices):
        CORE = 'core', 'Core'
        ELECTIVE = 'elective', 'Elective'
        APPLIED = 'applied', 'Applied'
        SPECIALIZED = 'specialized', 'Specialized'

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='program_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='program_links')
    kind = models.CharField(max_length=16, choices=Kind.choices)
    term = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'school_program_subjects'
        ordering = ['program', 'kind', 'subject__name']
        constraints = [
            models.UniqueConstraint(fields=['program', 'subject'], name='unique_subject_per_program'),
            models.CheckConstraint(
                condition=models.Q(term__isnull=True) | (models.Q(term__gte=1) & models.Q(term__lte=3)),
                name='program_subject_term_1_to_3',
            ),
        ]

    def __str__(self):
        return f'{self.program.code} {self.subject.code}'


class Section(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_PROGRESS = 'in_progress', 'In progress'
        READY = 'ready', 'Ready'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=64)
    grade_level = models.CharField(max_length=32, db_index=True)
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections',
    )
    capacity = models.PositiveSmallIntegerField(default=40)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'school_sections'
        ordering = ['grade_level', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school_year', 'name'],
                name='unique_section_name_per_year',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.school_year.label})'

    def save(self, *args, **kwargs):
        if self.program_id:
            self.program.check_grade(self.grade_level)
        super().save(*args, **kwargs)
