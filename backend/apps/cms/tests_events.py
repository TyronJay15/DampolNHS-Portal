from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cms.models import Announcement
from apps.notifications.models import Notification


class AnnouncementEventTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            first_name='School',
            last_name='Admin',
            role=User.Role.ADMIN,
        )
        self.client = APIClient()
        self.today = timezone.localdate()

    def _event(self, **kwargs):
        payload = {
            'title': 'Foundation Day',
            'body': 'Campus program.',
            'kind': Announcement.Kind.EVENT,
            'event_date': self.today + timedelta(days=3),
            'is_published': True,
            'published_at': timezone.now(),
        }
        payload.update(kwargs)
        return Announcement.objects.create(**payload)

    def test_existing_posts_default_to_news(self):
        row = Announcement.objects.create(title='Old post', body='News copy', is_published=True)
        self.assertEqual(row.kind, Announcement.Kind.NEWS)

    def test_cannot_publish_event_without_date(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/announcements/',
            {'title': 'Undated', 'body': 'Needs a date', 'kind': 'event', 'is_published': True},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('event_date', response.data.get('errors', response.data))

    def test_upcoming_lists_future_events_only(self):
        self._event(title='Soon', event_date=self.today + timedelta(days=2))
        self._event(title='Past', event_date=self.today - timedelta(days=2), is_published=True)
        self._event(
            title='Ongoing',
            event_date=self.today - timedelta(days=1),
            event_end_date=self.today + timedelta(days=1),
        )
        Announcement.objects.create(
            title='News',
            body='Not an event',
            kind=Announcement.Kind.NEWS,
            is_published=True,
            published_at=timezone.now(),
        )

        response = self.client.get('/api/announcements/?kind=event&upcoming=1')
        self.assertEqual(response.status_code, 200)
        titles = [row['title'] for row in response.data]
        self.assertEqual(titles, ['Ongoing', 'Soon'])

    def test_news_filter_hides_events(self):
        self._event()
        Announcement.objects.create(
            title='Campus news',
            body='Shown on landing',
            kind=Announcement.Kind.NEWS,
            is_published=True,
            published_at=timezone.now(),
        )
        response = self.client.get('/api/announcements/?kind=news')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['title'] for row in response.data], ['Campus news'])

    def test_publishing_event_notifies_active_users(self):
        teacher = User.objects.create_user(
            email='teacher@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/announcements/',
            {
                'title': 'Foundation Day',
                'body': 'Campus program.',
                'kind': 'event',
                'event_date': self.today + timedelta(days=3),
                'publish_to': 'both',
                'is_published': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Notification.objects.filter(user=teacher, title='Upcoming event: Foundation Day').exists())
        self.assertTrue(Notification.objects.filter(user=self.admin, title='Upcoming event: Foundation Day').exists())
