from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chatbot.models import FaqEntry
from apps.ml.forecast import attach_attractiveness, snapshot_year, train_forecast
from apps.ml.intent import classify_question, train_intent
from apps.ml.knn_model import rank_trained, train_knn
from apps.ml.store import last_run
from apps.people.models import Registration
from apps.school.forecast import build_grade11_forecast
from apps.school.models import Program, SchoolYear


class IntentModelTests(TestCase):
    def setUp(self):
        FaqEntry.objects.create(
            topic='registration',
            keywords='register, sign up',
            question='How do I register?',
            answer='Open Register and submit the form.',
        )
        train_intent()

    def test_classifies_registration(self):
        topic, confidence = classify_question('How do I register?')
        self.assertEqual(topic, 'registration')
        self.assertGreater(confidence, 0.4)

    def test_chatbot_uses_trained_topic(self):
        response = APIClient().post('/api/chatbot/', {'question': 'How do I sign up?'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['topic'], 'registration')
        self.assertIn('Register', response.data['answer'])

    def test_assistant_is_admin_only(self):
        admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            role=User.Role.ADMIN,
        )
        client = APIClient()
        self.assertEqual(client.get('/api/ml/assistant/').status_code, 401)
        client.force_authenticate(user=admin)
        response = client.get('/api/ml/assistant/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['intent']['ready'])
        self.assertNotIn('GEMINI', str(response.data))


class ForecastModelTests(TestCase):
    def setUp(self):
        self.stemc = Program.objects.create(code='STEMC', name='STEM Cluster', sort_order=1)
        self.admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            role=User.Role.ADMIN,
        )
        for index, label in enumerate(('2023-2024', '2024-2025', '2025-2026')):
            year = SchoolYear.objects.create(label=label, is_current=label.endswith('2026'))
            for _count in range(index + 2):
                user = User.objects.create_user(
                    email=f'{label}{_count}@example.com',
                    password='Strongpass1',
                    role=User.Role.STUDENT,
                )
                Registration.objects.create(
                    user=user,
                    school_year=year,
                    program=self.stemc,
                    grade_level_enrollment='Grade 11',
                    status=Registration.Status.APPROVED,
                )
            snapshot_year(year)

    def test_one_year_is_not_ready(self):
        old_years = SchoolYear.objects.exclude(label='2025-2026')
        Registration.objects.filter(school_year__in=old_years).delete()
        old_years.delete()
        run = train_forecast()
        self.assertFalse(run.metrics['ready'])
        payload = attach_attractiveness(build_grade11_forecast())
        self.assertEqual(payload['method'], 'counts')
        self.assertFalse(payload['ready'])

    def test_three_years_trains_regression(self):
        run = train_forecast()
        self.assertTrue(run.metrics['ready'])
        payload = attach_attractiveness(build_grade11_forecast())
        self.assertEqual(payload['method'], 'linear_regression')
        stemc = next(row for row in payload['clusters'] if row['code'] == 'STEMC')
        self.assertIsNotNone(stemc['projected'])
        self.assertEqual(stemc['rank'], 1)


class KnnModelTests(TestCase):
    def test_train_chooses_k_and_ranks(self):
        run = train_knn()
        self.assertIn(run.metrics['k'], (3, 5, 7))
        self.assertTrue(last_run('knn'))
        ranked = rank_trained({'math': 90, 'science': 88, 'language': 70, 'tech': 70}, 'STEMC')
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]['code'], 'bsce')
