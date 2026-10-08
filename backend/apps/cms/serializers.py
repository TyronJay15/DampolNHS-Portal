from rest_framework import serializers

from apps.cms.links import validate_link_field
from apps.cms.models import Announcement


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
            'publish_to',
            'is_published',
            'published_at',
            'created_at',
        )
        read_only_fields = ('published_at', 'created_at')

    def validate_image(self, value):
        return validate_link_field(value)

    def validate(self, attrs):
        kind = attrs.get('kind', getattr(self.instance, 'kind', Announcement.Kind.NEWS))
        event_date = attrs.get('event_date', getattr(self.instance, 'event_date', None))
        published = attrs.get('is_published', getattr(self.instance, 'is_published', False))
        if kind == Announcement.Kind.EVENT and published and not event_date:
            raise serializers.ValidationError(
                {'event_date': 'An event needs a date before it can be published.'}
            )
        return attrs
