"""Publish to: Website, Dashboard or Both. One record, shown on each surface its destination includes, only when
published."""

from datetime import timedelta
from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cms.models import Announcement
from apps.notifications.models import Notification

WEBSITE, DASHBOARD, BOTH = 'website', 'dashboard', 'both'


def make_user(email, role):
    return User.objects.create_user(
        email=email, password='Strongpass1!', role=role,
        approval_status=User.ApprovalStatus.APPROVED, account_status=User.AccountStatus.ACTIVE,
    )


class PublishToFixture(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.admin = make_user('admin@x.com', User.Role.ADMIN)
        self.student = make_user('student@x.com', User.Role.STUDENT)

    def event(self, publish_to, published=True, days=3, **extra):
        return Announcement.objects.create(
            title=f'{publish_to} event', body='Program.', kind=Announcement.Kind.EVENT,
            event_date=self.today + timedelta(days=days), publish_to=publish_to, is_published=published,
            published_at=timezone.now() if published else None, **extra,
        )

    def website_ids(self):
        """What the landing page shows: news plus upcoming events, as an anonymous visitor."""
        client = APIClient()
        news = client.get('/api/announcements/', {'kind': 'news', 'surface': 'website'}).data
        events = client.get('/api/announcements/', {'kind': 'event', 'upcoming': 1, 'surface': 'website'}).data
        return {row['id'] for row in [*news, *events]}

    def dashboard_ids(self, user=None):
        """What a signed-in user's Upcoming Events shows."""
        client = APIClient()
        client.force_authenticate(user or self.student)
        return {row['id'] for row in client.get('/api/announcements/', {'kind': 'event', 'upcoming': 1, 'surface': 'dashboard'}).data}

    def places(self, row):
        return (row.pk in self.website_ids(), row.pk in self.dashboard_ids())


class DestinationTests(PublishToFixture):
    def test_each_destination_shows_only_where_it_says(self):
        cases = {
            (WEBSITE, True): (True, False),
            (DASHBOARD, True): (False, True),
            (BOTH, True): (True, True),
            (WEBSITE, False): (False, False),
            (DASHBOARD, False): (False, False),
            (BOTH, False): (False, False),
        }
        for (publish_to, published), expected in cases.items():
            row = self.event(publish_to, published=published)
            self.assertEqual(self.places(row), expected, (publish_to, published))

    def test_both_is_one_record_in_both_places(self):
        row = self.event(BOTH)
        self.assertEqual(Announcement.objects.count(), 1)
        self.assertEqual(self.places(row), (True, True))

    def test_news_follows_its_destination_on_the_website(self):
        website = Announcement.objects.create(title='A', body='x', publish_to=WEBSITE, is_published=True)
        dashboard_only = Announcement.objects.create(title='B', body='x', publish_to=DASHBOARD, is_published=True)
        both = Announcement.objects.create(title='C', body='x', publish_to=BOTH, is_published=True)
        self.assertEqual(self.website_ids() & {website.pk, dashboard_only.pk, both.pk}, {website.pk, both.pk})

    def test_an_admin_dashboard_never_shows_drafts(self):
        draft = self.event(BOTH, published=False)
        self.assertNotIn(draft.pk, self.dashboard_ids(self.admin))

    def test_signed_out_visitors_get_no_dashboard_posts(self):
        self.event(DASHBOARD)
        self.event(BOTH)
        response = APIClient().get('/api/announcements/', {'surface': 'dashboard'})
        self.assertEqual((response.status_code, response.data), (200, []))

    def test_a_dashboard_only_post_cannot_be_read_on_the_website_by_id(self):
        row = self.event(DASHBOARD)
        self.assertEqual(APIClient().get(f'/api/announcements/{row.pk}/').status_code, 404)

    def test_past_events_follow_the_existing_upcoming_rule(self):
        past = self.event(BOTH, days=-3)
        ongoing = self.event(BOTH, days=-2, event_end_date=self.today)
        self.assertEqual(self.places(past), (False, False))
        self.assertEqual(self.places(ongoing), (True, True))

    def test_every_portal_role_sees_dashboard_events(self):
        row = self.event(DASHBOARD)
        for role in User.Role.values:
            self.assertIn(row.pk, self.dashboard_ids(make_user(f'{role}@y.com', role)), role)


class EditingTests(PublishToFixture):
    def change(self, row, **fields):
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.patch(f'/api/announcements/{row.pk}/', fields, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        row.refresh_from_db()

    def test_moving_a_post_moves_it_between_the_surfaces(self):
        row = self.event(WEBSITE)
        steps = [
            (DASHBOARD, (False, True)),
            (WEBSITE, (True, False)),
            (BOTH, (True, True)),
            (DASHBOARD, (False, True)),
        ]
        for publish_to, expected in steps:
            self.change(row, publish_to=publish_to)
            self.assertEqual(self.places(row), expected, publish_to)
        self.assertEqual(Announcement.objects.count(), 1)

    def test_an_edit_shows_in_both_places_at_once(self):
        row = self.event(BOTH)
        self.change(row, title='Foundation Day (moved)')
        public = APIClient().get(f'/api/announcements/{row.pk}/').data['title']
        self.assertEqual(public, 'Foundation Day (moved)')

    def test_unpublishing_or_deleting_removes_it_everywhere(self):
        row = self.event(BOTH)
        self.change(row, is_published=False)
        self.assertEqual(self.places(row), (False, False))
        self.change(row, is_published=True)
        client = APIClient()
        client.force_authenticate(self.admin)
        self.assertEqual(client.delete(f'/api/announcements/{row.pk}/').status_code, 204)
        self.assertEqual(self.places(row), (False, False))

    def test_the_cms_list_still_shows_every_post_with_its_destination(self):
        self.event(WEBSITE, published=False)
        self.event(DASHBOARD)
        client = APIClient()
        client.force_authenticate(self.admin)
        rows = client.get('/api/announcements/').data
        self.assertEqual(sorted(row['publish_to'] for row in rows), [DASHBOARD, WEBSITE])


class NotificationTests(PublishToFixture):
    def publish(self, publish_to):
        client = APIClient()
        client.force_authenticate(self.admin)
        body = {
            'title': f'{publish_to} day', 'body': 'x', 'kind': 'event',
            'event_date': self.today + timedelta(days=2), 'publish_to': publish_to, 'is_published': True,
        }
        self.assertEqual(client.post('/api/announcements/', body, format='json').status_code, 201)

    def test_only_events_that_reach_the_dashboards_notify_portal_users(self):
        self.publish(WEBSITE)
        self.assertFalse(Notification.objects.filter(title__startswith='Upcoming event').exists())
        self.publish(DASHBOARD)
        self.assertTrue(Notification.objects.filter(user=self.student, title='Upcoming event: dashboard day').exists())

    def test_moving_a_published_event_onto_the_dashboards_notifies_once(self):
        row = self.event(WEBSITE)
        client = APIClient()
        client.force_authenticate(self.admin)
        client.patch(f'/api/announcements/{row.pk}/', {'publish_to': BOTH}, format='json')
        client.patch(f'/api/announcements/{row.pk}/', {'publish_to': DASHBOARD}, format='json')
        self.assertEqual(Notification.objects.filter(user=self.student, title=f'Upcoming event: {row.title}').count(), 1)


class MigrationTests(TestCase):
    def test_existing_posts_keep_showing_where_they_did(self):
        migration = import_module('apps.cms.migrations.0004_announcement_publish_to')
        news = Announcement.objects.create(title='News', body='x', is_published=True)
        event = Announcement.objects.create(
            title='Event', body='x', kind=Announcement.Kind.EVENT, event_date=timezone.localdate(), is_published=True
        )
        migration.keep_current_places(django_apps, None)
        news.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual((news.publish_to, event.publish_to), (WEBSITE, BOTH))
        self.assertEqual(Announcement.objects.count(), 2)


class DashboardNewsTests(PublishToFixture):
    """News in the dashboards' Announcements section: the same publish_to rule, never mixed into Upcoming events."""

    def news(self, publish_to, published=True):
        return Announcement.objects.create(
            title=f'{publish_to} news', body='Notice.', publish_to=publish_to, is_published=published,
            published_at=timezone.now() if published else None,
        )

    def dashboard_news_ids(self, user=None):
        client = APIClient()
        client.force_authenticate(user or self.student)
        return {row['id'] for row in client.get('/api/announcements/', {'kind': 'news', 'surface': 'dashboard'}).data}

    def news_places(self, row):
        return (row.pk in self.website_ids(), row.pk in self.dashboard_news_ids())

    def test_each_destination_shows_only_where_it_says(self):
        cases = {
            (WEBSITE, True): (True, False),
            (DASHBOARD, True): (False, True),
            (BOTH, True): (True, True),
            (WEBSITE, False): (False, False),
            (DASHBOARD, False): (False, False),
            (BOTH, False): (False, False),
        }
        for (publish_to, published), expected in cases.items():
            self.assertEqual(self.news_places(self.news(publish_to, published)), expected, (publish_to, published))

    def test_every_portal_role_sees_dashboard_announcements(self):
        row = self.news(DASHBOARD)
        for role in User.Role.values:
            self.assertIn(row.pk, self.dashboard_news_ids(make_user(f'{role}@z.com', role)), role)

    def test_signed_out_visitors_cannot_reach_dashboard_news(self):
        row = self.news(DASHBOARD)
        listed = APIClient().get('/api/announcements/', {'kind': 'news', 'surface': 'dashboard'})
        self.assertEqual((listed.status_code, listed.data), (200, []))
        self.assertEqual(APIClient().get(f'/api/announcements/{row.pk}/').status_code, 404)

    def test_news_never_appears_in_upcoming_events(self):
        row = self.news(BOTH)
        self.assertNotIn(row.pk, self.dashboard_ids())

    def test_edits_unpublish_and_delete_move_one_record(self):
        row = self.news(WEBSITE)
        client = APIClient()
        client.force_authenticate(self.admin)
        for publish_to, expected in ((DASHBOARD, (False, True)), (BOTH, (True, True))):
            client.patch(f'/api/announcements/{row.pk}/', {'publish_to': publish_to}, format='json')
            self.assertEqual(self.news_places(row), expected, publish_to)
        self.assertEqual(Announcement.objects.count(), 1)
        client.patch(f'/api/announcements/{row.pk}/', {'is_published': False}, format='json')
        self.assertEqual(self.news_places(row), (False, False))
        client.patch(f'/api/announcements/{row.pk}/', {'is_published': True}, format='json')
        self.assertEqual(client.delete(f'/api/announcements/{row.pk}/').status_code, 204)
        self.assertEqual(self.news_places(row), (False, False))

    def test_dashboard_news_notifies_once_and_website_news_never(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        for publish_to in (WEBSITE, BOTH):
            body = {'title': f'{publish_to} notice', 'body': 'x', 'kind': 'news', 'publish_to': publish_to, 'is_published': True}
            self.assertEqual(client.post('/api/announcements/', body, format='json').status_code, 201)
        self.assertFalse(Notification.objects.filter(title='Announcement: website notice').exists())
        self.assertEqual(Notification.objects.filter(user=self.student, title='Announcement: both notice').count(), 1)
        row = Announcement.objects.get(title='both notice')
        client.patch(f'/api/announcements/{row.pk}/', {'publish_to': DASHBOARD}, format='json')
        self.assertEqual(Notification.objects.filter(user=self.student, title='Announcement: both notice').count(), 1)
