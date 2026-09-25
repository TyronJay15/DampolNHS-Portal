from django.conf import settings
from django.db import models


class Registration(models.Model):
    """Student signup waiting for administrator approval."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registration',
    )
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.PROTECT,
        related_name='registrations',
    )
    program = models.ForeignKey(
        'school.Program',
        on_delete=models.PROTECT,
        related_name='registrations',
    )
    previous_school = models.CharField(max_length=255, blank=True)
    grade_level_current = models.CharField(max_length=32, blank=True)
    grade_level_enrollment = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations_reviewed',
    )

    class Meta:
        db_table = 'people_registrations'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.email} ({self.status})'


class TeacherAssignment(models.Model):
    class Type(models.TextChoices):
        SUBJECT_TEACHER = 'subject_teacher', 'Subject teacher'
        ADVISER = 'adviser', 'Adviser'
        HEAD_TEACHER = 'head_teacher', 'Head teacher'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
        limit_choices_to={'role': 'teacher'},
    )
    assignment_type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
    )
    subject = models.ForeignKey(
        'school.Subject',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teacher_assignments',
    )
    section = models.ForeignKey(
        'school.Section',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teacher_assignments',
    )
    grade_level = models.CharField(max_length=32, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_assignments_made',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'people_teacher_assignments'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'assignment_type', 'school_year', 'grade_level', 'section', 'subject'],
                condition=models.Q(status='active'),
                name='unique_active_teacher_assignment',
            ),
            models.UniqueConstraint(
                fields=['section', 'school_year'],
                condition=models.Q(status='active', assignment_type='adviser'),
                name='unique_active_adviser_per_section',
            ),
            models.UniqueConstraint(
                fields=['grade_level', 'school_year'],
                condition=models.Q(status='active', assignment_type='head_teacher'),
                name='unique_active_head_teacher_per_grade',
            ),
        ]

    def __str__(self):
        return f'{self.teacher.email} — {self.assignment_type}'


class StudentSection(models.Model):
    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='section_assignments',
    )
    section = models.ForeignKey(
        'school.Section',
        on_delete=models.PROTECT,
        related_name='student_assignments',
    )
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.PROTECT,
        related_name='student_section_assignments',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_sections_assigned',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'people_student_sections'
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'school_year'],
                condition=models.Q(is_active=True),
                name='unique_active_section_per_student_year',
            ),
        ]

    def __str__(self):
        return f'{self.student.lrn} → {self.section.name}'
