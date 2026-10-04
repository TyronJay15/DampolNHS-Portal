"""Saving website content, shared by the Admin's CMS screens and approved access requests."""

import json

from django.core.files.storage import default_storage
from django.utils import timezone

from apps.audit import services as audit
from apps.audit.catalog import ANNOUNCEMENTS
from apps.cms.media import uploaded_name
from apps.cms.models import Announcement, SiteContent
from apps.notifications.services import active_users, notify


def clean_payload(document, payload):
    if document != SiteContent.Document.LANDING or not isinstance(payload, dict):
        return payload
    cleaned = dict(payload)
    cleaned.pop('bulletinCards', None)
    return cleaned


def live_document(document):
    row = SiteContent.objects.filter(document=document).first()
    return dict(row.payload) if row and isinstance(row.payload, dict) else {}


def save_document(document, payload, actor):
    """Publish a whole CMS page (landing, about, contact or footer)."""
    payload = clean_payload(document, payload)
    row, _created = SiteContent.objects.update_or_create(
        document=document,
        defaults={'payload': payload, 'updated_by': actor},
    )
    audit.record(
        user=actor,
        action='cms_save',
        summary=f'Saved CMS document {document}',
        target_type='SiteContent',
        target_id=row.id,
    )
    return row


def save_new_announcement(serializer, actor):
    """Save a validated new post; an event published now is announced on every dashboard."""
    published = serializer.validated_data.get('is_published')
    row = serializer.save(created_by=actor, published_at=timezone.now() if published else None)
    _notify_event(row, was_published=False)
    return row


def save_announcement_changes(serializer):
    """Save validated changes to a post, keeping published_at in step with is_published."""
    instance = serializer.instance
    was_published = instance.is_published
    published = serializer.validated_data.get('is_published', instance.is_published)
    extra = {}
    if published and not instance.published_at:
        extra['published_at'] = timezone.now()
    if not published:
        extra['published_at'] = None
    row = serializer.save(**extra)
    _notify_event(row, was_published=was_published)
    return row


def _notify_event(row, was_published):
    if row.kind != Announcement.Kind.EVENT or not row.is_published or was_published:
        return
    when = row.event_date.strftime('%b %d, %Y') if row.event_date else 'soon'
    notify(
        active_users(),
        title=f'Upcoming event: {row.title}',
        body=f'{row.title} is on {when}{f" · {row.location}" if row.location else ""}.',
        category=ANNOUNCEMENTS,
    )


def upload_urls(value):
    """Every uploaded CMS photo URL found anywhere inside a value (text, list or dict)."""
    found = set()
    if isinstance(value, str):
        if uploaded_name(value):
            found.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            found |= upload_urls(item)
    elif isinstance(value, list):
        for item in value:
            found |= upload_urls(item)
    return found


def is_in_use(url):
    """True when a published page or any post still shows this photo."""
    if Announcement.objects.filter(image=url).exists():
        return True
    return any(url in json.dumps(row.payload) for row in SiteContent.objects.all())


def delete_unused_uploads(urls):
    """Delete uploaded photos nobody uses (e.g. from a declined proposal). Photos in use are kept."""
    for url in urls:
        name = uploaded_name(url)
        if name and not is_in_use(url) and default_storage.exists(name):
            default_storage.delete(name)
