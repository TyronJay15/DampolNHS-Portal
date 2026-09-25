from django.conf import settings
from django.db import models


class SiteContent(models.Model):
    """One named document of public website copy. Payload is text only, never executed."""

    class Document(models.TextChoices):
        LANDING = 'landing', 'Landing'
        ABOUT = 'about', 'About'
        CONTACT = 'contact', 'Contact'
        FOOTER = 'footer', 'Footer'

    document = models.CharField(max_length=32, choices=Document.choices, unique=True)
    payload = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cms_updates',
    )

    class Meta:
        db_table = 'cms_site_content'

    def __str__(self):
        return self.document


class Announcement(models.Model):
    class Kind(models.TextChoices):
        NEWS = 'news', 'News'
        EVENT = 'event', 'Event'

    title = models.CharField(max_length=200)
    body = models.TextField()
    image = models.CharField(max_length=400, blank=True)
    category = models.CharField(max_length=50, blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.NEWS, db_index=True)
    event_date = models.DateField(null=True, blank=True)
    event_end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
    )

    class Meta:
        db_table = 'cms_announcements'
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title
