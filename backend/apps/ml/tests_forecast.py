"""Enrollment planning: live counts, the Grade 12 retention estimate and the Grade 11 trend (numbered as in the spec)."""

from datetime import datetime
from decimal import Decimal
from io import StringIO
from unittest import mock

import numpy as np
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.ml import regression
from apps.ml.forecast import CONFIDENT, LOW_CONFIDENCE, UNTESTED, attach_attractiveness, train_forecast
from apps.ml.models import ClusterSnapshot, ModelRun
from apps.ml.regression import fit_line, forward_tests
from apps.people.models import Registration
from apps.school.forecast import build_grade11_forecast, expected_students, sections_needed
from apps.school.models import Curriculum, Program, SchoolYear, SchoolYearCurriculum, Section

APPROVED = Registration.Status.APPROVED
PENDING = Registration.Status.PENDING
REJECTED = Registration.Status.REJECTED
FORECAST_URL = '/api/admin/forecast/'
RETENTION_URL = '/api/admin/forecast/retention/'


def manila(year, month, day):
    return timezone.make_aware(datetime(year, month, day, 12))


class PlanningFixture(TestCase):
    def setUp(self):
        self.sshs = Curriculum.objects.get(code='strengthened-shs')
        self.k12 = Curriculum.objects.get(code='k12-shs')
        stem = Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12', curriculum=self.sshs)
        abm = Program.objects.create(code='ABM', name='ABM', grade_level='Grade 12', curriculum=self.sshs)
        self.stemc = Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11', curriculum=self.sshs, continues_to=stem, sort_order=1)
        self.be = Program.objects.create(code='BE', name='Business', grade_level='Grade 11', curriculum=self.sshs, continues_to=abm, sort_order=2)
        self.current = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.admin = User.objects.create_user(email='admin@x.com', password='Strongpass1', role=User.Role.ADMIN)
        self.serial = 0

    def register(self, program, status=APPROVED, submitted=None, year=None):
        self.serial += 1
        user = User.objects.create_user(email=f's{self.serial}@x.com', password=None, role=User.Role.STUDENT)
        row = Registration.objects.create(
            user=user,
            school_year=year or self.current,
            program=program,
            grade_level_enrollment=program.grade_level,
            status=status,
        )
        if submitted:
            Registration.objects.filter(pk=row.pk).update(submitted_at=submitted)
        return row

    def history(self, label, counts, curriculum=None):
        """A completed year with stored Grade 11 counts, e.g. counts={stemc: 40}."""
        year = SchoolYear.objects.create(label=label, archived_at=timezone.now())
        if curriculum:
            SchoolYearCurriculum.objects.create(school_year=year, grade_level='Grade 11', curriculum=curriculum)
        for program, applied in counts.items():
            ClusterSnapshot.objects.create(
                school_year=year,
                cluster_code=program.code,
                program=program,
                curriculum=curriculum or program.curriculum,
                applied_count=applied,
                approved_count=applied,
            )
        return year

    def planning(self):
        return attach_attractiveness(build_grade11_forecast())

    def row(self, payload, code):
        return next(item for item in payload['clusters'] if item['code'] == code)

    def client_for(self, role):
        client = APIClient()
        user = self.admin if role == User.Role.ADMIN else User.objects.create_user(email=f'{role}@x.com', password='Strongpass1', role=role)
        client.force_authenticate(user=user)
        return client


class LiveStatisticsTests(PlanningFixture):
    def setUp(self):
        super().setUp()
        for status in (APPROVED, APPROVED, APPROVED, PENDING, REJECTED, REJECTED):
            self.register(self.stemc, status)
        self.register(self.be, APPROVED)

    def test_01_live_applicant_counts(self):
        payload = build_grade11_forecast()
        self.assertEqual((payload['applied_total'], payload['grade11_total']), (5, 4))

    def test_02_rejected_records_are_not_demand(self):
        payload = build_grade11_forecast()
        self.assertEqual(self.row(payload, 'STEMC')['applied'], 4)
        self.assertEqual(payload['selection']['rejected_excluded'], 2)

    def test_03_approval_rate(self):
        self.assertEqual(build_grade11_forecast()['approval_rate'], 80.0)

    def test_04_per_program_counts_and_rates(self):
        payload = build_grade11_forecast()
        stemc, be = self.row(payload, 'STEMC'), self.row(payload, 'BE')
        self.assertEqual((stemc['applied'], stemc['count'], stemc['approval_rate']), (4, 3, 75.0))
        self.assertEqual((be['applied'], be['count'], be['approval_rate']), (1, 1, 100.0))


class WeeklyTests(PlanningFixture):
    def test_05_weekly_cumulative_totals(self):
        self.register(self.stemc, PENDING, manila(2026, 6, 1))
        self.register(self.stemc, APPROVED, manila(2026, 6, 1))
        self.register(self.be, APPROVED, manila(2026, 6, 3))
        self.register(self.be, REJECTED, manila(2026, 6, 9))
        self.register(self.stemc, APPROVED, manila(2026, 6, 17))
        weekly = build_grade11_forecast()['weekly']
        self.assertEqual(
            weekly,
            [
                {'week_start': '2026-06-01', 'added': 3, 'total': 3},
                {'week_start': '2026-06-08', 'added': 0, 'total': 3},
                {'week_start': '2026-06-15', 'added': 1, 'total': 4},
            ],
        )


class Grade12PlanTests(PlanningFixture):
    def setUp(self):
        super().setUp()
        Section.objects.create(school_year=self.current, name='STEMC-A', grade_level='Grade 11', program=self.stemc, capacity=2)
        for _index in range(3):
            self.register(self.stemc, APPROVED)
        self.register(self.be, APPROVED)

    def strand(self, code):
        return next(item for item in build_grade11_forecast()['strands'] if item['code'] == code)

    def test_06_retention_at_100_percent(self):
        stem = self.strand('STEM')
        self.assertEqual((stem['count'], stem['expected'], stem['sections_needed']), (3, 3, 2))

    def test_07_retention_below_100_percent(self):
        SchoolYear.objects.filter(pk=self.current.pk).update(retention_rate=Decimal('50'))
        stem = self.strand('STEM')
        self.assertEqual((stem['count'], stem['expected'], stem['sections_needed']), (3, 2, 1))
        self.assertEqual(expected_students(46, Decimal('87.5')), 40)

    def test_08_sections_round_up(self):
        self.assertEqual([sections_needed(41, 40), sections_needed(40, 40), sections_needed(0, 40)], [2, 1, 0])
        self.assertEqual(sections_needed(46, 40), 2)

    def test_09_leads_to_mapping_is_used(self):
        payload = build_grade11_forecast()
        self.assertEqual({item['code']: item['from_codes'] for item in payload['strands']}, {'STEM': ['STEMC'], 'ABM': ['BE']})
        self.be.continues_to = None
        self.be.save(update_fields=['continues_to'])
        self.assertEqual(build_grade11_forecast()['grade12_unmapped'], ['BE'])


class TrendGateTests(PlanningFixture):
    def test_10_locked_with_fewer_than_three_completed_years(self):
        self.history('2024-2025', {self.stemc: 30})
        self.history('2025-2026', {self.stemc: 34})
        self.register(self.stemc, APPROVED)
        run = train_forecast()
        self.assertFalse(run.metrics['ready'])
        payload = self.planning()
        self.assertEqual((payload['trend']['status'], payload['trend']['completed_years']), ('locked', 2))
        self.assertIn('1 more completed school year', payload['trend']['unlock_note'])
        stemc = self.row(payload, 'STEMC')
        self.assertEqual((stemc['next_intake_basis'], stemc['next_intake_note'], stemc['trend_status']), ('estimate', 'same as this year', 'locked'))
        self.assertIsNone(stemc['projected'])

    def test_11_other_curriculum_years_do_not_unlock(self):
        self.history('2023-2024', {self.stemc: 28}, curriculum=self.k12)
        self.history('2024-2025', {self.stemc: 30})
        self.history('2025-2026', {self.stemc: 34})
        self.assertFalse(train_forecast().metrics['ready'])
        self.assertEqual(self.planning()['trend']['completed_years'], 2)

    def test_12_unlocks_at_three_completed_years(self):
        for label, applied in (('2023-2024', 30), ('2024-2025', 34), ('2025-2026', 38)):
            self.history(label, {self.stemc: applied})
        run = train_forecast()
        self.assertTrue(run.metrics['ready'])
        stemc = self.row(self.planning(), 'STEMC')
        self.assertEqual((stemc['next_intake_basis'], stemc['trend_status'], stemc['projected']), ('forecast', UNTESTED, 46))
        self.assertEqual(stemc['direction'], 'rising')

    def test_estimate_falls_back_to_the_last_completed_year(self):
        self.history('2025-2026', {self.be: 25})
        stemc, be = self.row(self.planning(), 'STEMC'), self.row(self.planning(), 'BE')
        self.assertEqual((be['next_intake'], be['next_intake_note']), (25, 'same as the last completed year'))
        self.assertEqual(stemc['next_intake_note'], 'no data yet')


class RegressionTests(TestCase):
    def test_13_regression_is_reproducible(self):
        first, second = fit_line([0, 1, 2, 3], [20, 24, 23, 29]), fit_line([0, 1, 2, 3], [20, 24, 23, 29])
        self.assertEqual(first, second)
        slope, intercept = np.polyfit([0, 1, 2, 3], [20, 24, 23, 29], 1)
        self.assertAlmostEqual(first['slope'], slope)
        self.assertAlmostEqual(first['intercept'], intercept)

    def test_14_forward_evaluation_never_sees_the_future(self):
        seen = []
        real = regression.fit_line

        def spy(xs, ys):
            seen.append(tuple(xs))
            return real(xs, ys)

        points = [(0, 10), (1, 12), (2, 15), (3, 16), (4, 20)]
        with mock.patch.object(regression, 'fit_line', side_effect=spy):
            tests = forward_tests(points, 3)
        self.assertEqual([test['x'] for test in tests], [3, 4])
        for test, xs in zip(tests, seen):
            self.assertLess(max(xs), test['x'])
            self.assertEqual(test['trained_through'], max(xs))


class EvaluationTests(PlanningFixture):
    def fit(self, counts):
        for offset, applied in enumerate(counts):
            self.history(f'{2020 + offset}-{2021 + offset}', {self.stemc: applied})
        return train_forecast()

    def test_15_trend_is_compared_with_the_baseline(self):
        run = self.fit([20, 25, 30, 35, 40])
        evaluation = run.metrics['evaluation']
        self.assertTrue(evaluation['evaluated'])
        self.assertEqual(evaluation['tests'], 2)
        self.assertLess(evaluation['rmse'], evaluation['baseline_rmse'])
        self.assertTrue(evaluation['beats_baseline'])
        self.assertEqual(run.artifact['models'][str(self.stemc.pk)]['status'], CONFIDENT)

    def test_16_a_trend_that_loses_to_the_baseline_is_low_confidence(self):
        run = self.fit([10, 20, 30, 30])
        model = run.artifact['models'][str(self.stemc.pk)]
        self.assertEqual(model['status'], LOW_CONFIDENCE)
        self.assertGreater(model['rmse'], model['baseline_rmse'])
        self.assertEqual(self.row(self.planning(), 'STEMC')['trend_status'], LOW_CONFIDENCE)


class PermissionTests(PlanningFixture):
    def test_17_to_19_only_the_admin_may_read_retrain_or_change_retention(self):
        for role in (User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.STUDENT):
            client = self.client_for(role)
            self.assertEqual(client.get(FORECAST_URL).status_code, 403, role)
            self.assertEqual(client.post(FORECAST_URL).status_code, 403, role)
            self.assertEqual(client.patch(RETENTION_URL, {'retention_rate': 90}, format='json').status_code, 403, role)
        anonymous = APIClient()
        self.assertEqual(anonymous.get(FORECAST_URL).status_code, 401)
        self.assertEqual(anonymous.patch(RETENTION_URL, {'retention_rate': 90}, format='json').status_code, 401)
        self.assertFalse(ModelRun.objects.exists())
        self.current.refresh_from_db()
        self.assertEqual(self.current.retention_rate, Decimal('100'))

    def test_retention_is_validated_on_the_server(self):
        client = self.client_for(User.Role.ADMIN)
        for bad in (101, -1, 'abc', 12.345):
            self.assertEqual(client.patch(RETENTION_URL, {'retention_rate': bad}, format='json').status_code, 400, bad)
        response = client.patch(RETENTION_URL, {'retention_rate': '87.5'}, format='json')
        self.assertEqual((response.status_code, response.data['retention_rate']), (200, '87.50'))


class DemoSeedTests(PlanningFixture):
    def test_20_demo_seeding_refuses_outside_demo_mode(self):
        with self.assertRaisesMessage(CommandError, 'DEMO_MODE is off'):
            call_command('seed_demo_forecast', stdout=StringIO())
        self.assertFalse(ClusterSnapshot.objects.exists())
        self.assertEqual(SchoolYear.objects.count(), 1)

    @override_settings(DEMO_MODE=True)
    def test_demo_seeding_is_marked_synthetic_and_can_be_removed(self):
        call_command('seed_demo_forecast', stdout=StringIO())
        self.assertTrue(ClusterSnapshot.objects.exists())
        self.assertFalse(ClusterSnapshot.objects.filter(is_synthetic=False).exists())
        payload = self.planning()
        self.assertEqual((payload['trend']['status'], payload['trend']['synthetic']), ('ready', True))
        call_command('seed_demo_forecast', '--remove', stdout=StringIO())
        self.assertEqual(SchoolYear.objects.count(), 1)
        self.assertFalse(self.planning()['trend']['synthetic'])


class ArchiveAndAuditTests(PlanningFixture):
    def test_21_to_23_archiving_snapshots_retrains_and_audits(self):
        finished = SchoolYear.objects.create(label='2025-2026')
        self.register(self.stemc, APPROVED, year=finished)
        self.register(self.stemc, APPROVED, year=finished)
        self.register(self.stemc, REJECTED, year=finished)
        head = self.client_for(User.Role.HEAD_TEACHER)
        self.assertEqual(head.post(f'/api/school-years/{finished.pk}/archive/').status_code, 200)
        snapshot = ClusterSnapshot.objects.get(school_year=finished, program=self.stemc)
        self.assertEqual((snapshot.applied_count, snapshot.approved_count, snapshot.curriculum, snapshot.is_synthetic), (2, 2, self.sshs, False))
        run = ModelRun.objects.get(name='forecast')
        self.assertEqual((run.algorithm, run.artifact['schema'], run.metrics['completed_years']), ('sklearn_linear_regression', 2, 1))
        self.assertTrue(AuditLog.objects.filter(action='model_trained', summary__contains='after archiving 2025-2026').exists())

    def test_forecast_error_does_not_undo_archive(self):
        finished = SchoolYear.objects.create(label='2025-2026')
        self.register(self.stemc, APPROVED, year=finished)
        head = self.client_for(User.Role.HEAD_TEACHER)
        with mock.patch('apps.ml.forecast.retrain', side_effect=RuntimeError('forecast down')):
            self.assertEqual(head.post(f'/api/school-years/{finished.pk}/archive/').status_code, 200)
        finished.refresh_from_db()
        self.assertIsNotNone(finished.archived_at)
        self.assertTrue(ClusterSnapshot.objects.filter(school_year=finished, program=self.stemc).exists())
        self.assertFalse(AuditLog.objects.filter(action='model_trained', summary__contains='after archiving 2025-2026').exists())

    def test_snapshot_error_rolls_back_archive(self):
        finished = SchoolYear.objects.create(label='2025-2026')
        head = APIClient(raise_request_exception=False)
        user = User.objects.create_user(email='head-snap@x.com', password='Strongpass1', role=User.Role.HEAD_TEACHER)
        head.force_authenticate(user=user)
        with mock.patch('apps.ml.forecast.snapshot_year', side_effect=RuntimeError('snapshot down')):
            self.assertEqual(head.post(f'/api/school-years/{finished.pk}/archive/').status_code, 500)
        finished.refresh_from_db()
        self.assertIsNone(finished.archived_at)

    def test_22_retrain_records_a_new_model_run(self):
        client = self.client_for(User.Role.ADMIN)
        client.post(FORECAST_URL)
        client.post(FORECAST_URL)
        self.assertEqual(list(ModelRun.objects.filter(name='forecast').order_by('-version').values_list('version', flat=True)), [2, 1])
        self.assertEqual(AuditLog.objects.filter(action='model_trained').count(), 2)

    def test_23_changing_retention_is_audited(self):
        client = self.client_for(User.Role.ADMIN)
        client.patch(RETENTION_URL, {'retention_rate': 90}, format='json')
        client.patch(RETENTION_URL, {'retention_rate': 90}, format='json')
        entries = AuditLog.objects.filter(action='retention_rate_changed')
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.get().details, {'before': '100.00', 'after': '90.00'})
