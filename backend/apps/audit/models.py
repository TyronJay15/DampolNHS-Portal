from django.conf import settings
from django.db import models


class AuditLogQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionError('Audit records cannot be deleted through the application.')

    def update(self, **kwargs):
        raise PermissionError('Audit records cannot be changed once written.')


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    actor_label = models.CharField(max_length=150, blank=True)
    actor_role = models.CharField(max_length=16, blank=True, db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError('Audit records cannot be changed once written.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit records cannot be deleted through the application.')

    def __str__(self):
        return f'{self.action}: {self.summary}'
