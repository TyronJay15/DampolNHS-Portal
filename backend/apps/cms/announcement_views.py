from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAdmin
from apps.cms.models import Announcement
from apps.notifications.services import active_users, notify


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            'id',
            'title',
            'body',
            'image',
            'category',
            'kind',
            'event_date',
            'event_end_date',
            'location',
            'is_published',
            'published_at',
            'created_at',
        )
        read_only_fields = ('published_at', 'created_at')

    def validate(self, attrs):
        kind = attrs.get('kind', getattr(self.instance, 'kind', Announcement.Kind.NEWS))
        event_date = attrs.get('event_date', getattr(self.instance, 'event_date', None))
        published = attrs.get('is_published', getattr(self.instance, 'is_published', False))
        if kind == Announcement.Kind.EVENT and published and not event_date:
            raise serializers.ValidationError(
                {'event_date': 'An event needs a date before it can be published.'}
            )
        return attrs


class AnnouncementViewSet(ModelViewSet):
    serializer_class = AnnouncementSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        qs = Announcement.objects.all()
        user = self.request.user
        if not (user.is_authenticated and getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(is_published=True)

        kind = self.request.query_params.get('kind')
        if kind in dict(Announcement.Kind.choices):
            qs = qs.filter(kind=kind)

        if self.request.query_params.get('upcoming') == '1':
            today = timezone.localdate()
            qs = qs.filter(kind=Announcement.Kind.EVENT).filter(
                Q(event_end_date__gte=today)
                | Q(event_end_date__isnull=True, event_date__gte=today)
            ).order_by('event_date', 'title')
        return qs

    def perform_create(self, serializer):
        published = serializer.validated_data.get('is_published')
        row = serializer.save(
            created_by=self.request.user,
            published_at=timezone.now() if published else None,
        )
        _notify_event(row, was_published=False)

    def perform_update(self, serializer):
        instance = self.get_object()
        was_published = instance.is_published
        published = serializer.validated_data.get('is_published', instance.is_published)
        extra = {}
        if published and not instance.published_at:
            extra['published_at'] = timezone.now()
        if not published:
            extra['published_at'] = None
        row = serializer.save(**extra)
        _notify_event(row, was_published=was_published)


def _notify_event(row, was_published):
    if row.kind != Announcement.Kind.EVENT or not row.is_published or was_published:
        return
    when = row.event_date.strftime('%b %d, %Y') if row.event_date else 'soon'
    notify(
        active_users(),
        title=f'Upcoming event: {row.title}',
        body=f'{row.title} is on {when}{f" · {row.location}" if row.location else ""}.',
    )
