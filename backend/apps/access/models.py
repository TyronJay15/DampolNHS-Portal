"""Access tags: an owner lets a person prepare one of the owner's activities.

The tagged person never changes anything directly. Each piece of work becomes an AccessRequest
that the owner approves (the system then runs the real action as the owner) or declines.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AccessTag(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'

    activity = models.CharField(max_length=40, db_index=True)
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_tags')
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_access_tags',
    )
    scope = models.CharField(
        max_length=32,
        blank=True,
        help_text='Grade level the tag is limited to; blank means every level the owner manages.',
    )
    ends_on = models.DateField(
        null=True,
        blank=True,
        help_text='Last day the tag works. Empty only when the owner chose "No end date".',
    )
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_access_tags',
    )
    close_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'access_tags'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.holder} · {self.activity} ({self.state})'

    @property
    def state(self):
        """active, ended (its end date passed) or closed (the owner closed it)."""
        if self.status == self.Status.CLOSED:
            return 'closed'
        if self.ends_on is not None and self.ends_on < timezone.localdate():
            return 'ended'
        return 'active'

    @property
    def is_live(self):
        return self.state == 'active'


class AccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Waiting for approval'
        APPROVED = 'approved', 'Approved'
        DECLINED = 'declined', 'Declined'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        EXPIRED = 'expired', 'Expired'
        FAILED = 'failed', 'Could not be applied'

    tag = models.ForeignKey(AccessTag, on_delete=models.CASCADE, related_name='requests')
    activity = models.CharField(max_length=40, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_requests')
    payload = models.JSONField(default=dict, help_text='Exactly what was proposed; the owner approves this.')
    summary = models.CharField(max_length=255)
    changes = models.JSONField(
        default=list,
        blank=True,
        help_text='Before and after, field by field, as it stood when the request was submitted.',
    )
    note = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decided_access_requests',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'access_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.summary} ({self.status})'
