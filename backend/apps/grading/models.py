from django.conf import settings
from django.db import models
from django.utils import timezone


class Grade(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        RELEASED = 'released', 'Released'

    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='grades',
    )
    subject = models.ForeignKey(
        'school.Subject',
        on_delete=models.PROTECT,
        related_name='grades',
    )
    term = models.ForeignKey(
        'school.Term',
        on_delete=models.PROTECT,
        related_name='grades',
    )
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.PROTECT,
        related_name='grades',
    )
    section = models.ForeignKey(
        'school.Section',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='grades',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encoded_grades',
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_grades',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grading_grades'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'subject', 'term'],
                name='unique_grade_per_student_subject_term',
            ),
        ]

    def __str__(self):
        return f'{self.student.lrn} {self.subject.name}: {self.score}'


class GradeHistory(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    previous_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grade_history_entries',
    )
    duty = models.CharField(max_length=20, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'grading_history'
        ordering = ['-changed_at']

    def save(self, *args, **kwargs):
        if self.pk and GradeHistory.objects.filter(pk=self.pk).exists():
            raise PermissionError('Grade history cannot be changed once written.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Grade history cannot be deleted.')


class CorrectionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='corrections')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='grade_corrections_requested',
    )
    current_score = models.DecimalField(max_digits=5, decimal_places=2)
    proposed_score = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grade_corrections_reviewed',
    )
    review_note = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'grading_corrections'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['grade'],
                condition=models.Q(status='pending'),
                name='one_open_correction_per_grade',
            ),
        ]

    def mark_reviewed(self, *, by_user, status, note=''):
        self.status = status
        self.reviewed_by = by_user
        self.review_note = note or ''
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewed_by', 'review_note', 'reviewed_at'])


class PtpaAttendance(models.Model):
    """Parent attendance for one student in one term. Show is blocked until True."""

    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='ptpa_records',
    )
    term = models.ForeignKey('school.Term', on_delete=models.CASCADE, related_name='ptpa_records')
    section = models.ForeignKey('school.Section', on_delete=models.CASCADE, related_name='ptpa_records')
    attended = models.BooleanField(default=False, db_index=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ptpa_marks',
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grading_ptpa'
        constraints = [
            models.UniqueConstraint(fields=['student', 'term'], name='one_ptpa_per_student_term'),
        ]

    def __str__(self):
        state = 'attended' if self.attended else 'absent'
        return f'{self.student.lrn} {self.term.label}: {state}'
