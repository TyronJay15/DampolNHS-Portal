from django.conf import settings
from django.db import models

from apps.audit.catalog import ACCOUNTS, FAMILIES


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        SUCCESS = 'success', 'Success'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=160)
    body = models.TextField()
    category = models.CharField(max_length=16, choices=[(row, row) for row in FAMILIES], default=ACCOUNTS, db_index=True)
    level = models.CharField(
        max_length=16,
        choices=Level.choices,
        default=Level.INFO,
        db_index=True,
    )
    action_path = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
