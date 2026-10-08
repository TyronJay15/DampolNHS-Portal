from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAdmin
from apps.access.services import live_tag
from apps.cms.models import SURFACES, Announcement
from apps.cms.serializers import AnnouncementSerializer
from apps.cms.services import on_surface, save_announcement_changes, save_new_announcement


class AnnouncementViewSet(ModelViewSet):
    serializer_class = AnnouncementSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        """?surface=website or ?surface=dashboard lists what that place shows: published posts whose "Publish to"
        includes it. Dashboard posts are for signed-in portal users only. Without a surface, the CMS (Admin and
        people tagged to post news) sees every post including drafts; anyone else sees the website's posts."""
        qs = Announcement.objects.all()
        user = self.request.user
        surface = self.request.query_params.get('surface')
        # Drafts are for the Admin and for people tagged to prepare news posts.
        sees_drafts = user.is_authenticated and (
            getattr(user, 'role', None) == 'admin' or live_tag(user, 'post_news') is not None
        )
        if surface == 'dashboard' and not user.is_authenticated:
            return qs.none()
        if surface in SURFACES:
            qs = on_surface(qs, surface)
        elif not sees_drafts:
            qs = on_surface(qs, 'website')

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
        save_new_announcement(serializer, self.request.user)

    def perform_update(self, serializer):
        save_announcement_changes(serializer)
