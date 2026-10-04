import math
from decimal import Decimal
from io import StringIO

from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.chatbot.admin import FaqEntryAdmin
from apps.chatbot.models import FaqEntry
from apps.chatbot.seeds import seed_faqs
from apps.grading.models import Grade
from apps.grading.recommend import RecommendationContext, recommend_payload
from apps.ml.features import load_schema, to_model_space, transform
from apps.ml.forecast import FEATURE_SCHEMA, attach_attractiveness, snapshot_year, train_forecast
from apps.ml.forecast import is_stale as forecast_is_stale
from apps.ml.intent import answers_for, classify_question, matching_faq_answer, train_intent
from apps.ml.intent import is_stale as intent_is_stale
from apps.ml.knn_model import (
    BELOW_MINIMUM,
    FAILED,
    INSUFFICIENT,
    LIMITED,
    NEEDS_DATA,
    PASSED,
    RANKED,
    STRONG,
    TRACK_BOOST,
    UNKNOWN,
    Ranking,
    compare_all,
    load_candidates,
    outcome_dataset,
    rank,
)
from apps.ml.models import ClusterSnapshot, CollegeOutcome, CollegeProgram, CollegeProgramSkill, ModelRun
from apps.ml.seed import seed_college_programs
from apps.ml.regression import fit_line, predict_line
from apps.ml.store import KEEP_RUNS, last_run, save_run
from apps.people.models import Registration, StudentSection
from apps.school.curriculum import curriculum_for, freeze_year, programs_for
from apps.school.forecast import build_grade11_forecast
from apps.school.offerings import (
    seed_academic_reference,
    seed_matching_exclusions,
    seed_programs,
    sync_subject_catalog,
)
from apps.school.models import (
    Curriculum,
    Program,
    SchoolYear,
    SchoolYearCurriculum,
    Section,
    SkillDomain,
    Subject,
    Term,
)


def strongest_domain(college_code):
    program = CollegeProgram.objects.get(code=college_code)
    return max(program.skills.all(), key=lambda row: row.level).domain.key


class AcademicDataMixin:
    """Builds real school rows through the ORM, the way the admin does."""

    def setUp(self):
        super().setUp()
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.subjects = {}
        self._serial = 0

    def subject(self, code, domain_key):
        if code not in self.subjects:
            domain = SkillDomain.objects.get(key=domain_key) if domain_key else None
            self.subjects[code] = Subject.objects.create(code=code, name=code.title(), skill_domain=domain)
        return self.subjects[code]

    def student(self, scores, status=Grade.Status.RELEASED):
        """scores: {(subject_code, domain_key): score}. Returns the profile and its grades."""
        self._serial += 1
        user = User.objects.create_user(
            email=f'learner{self._serial}@example.com',
            password='Strongpass1',
            role=User.Role.STUDENT,
        )
        profile = StudentProfile.objects.create(user=user, lrn=f'1360000{self._serial:05d}')
        grades = [
            Grade.objects.create(
                student=profile,
                subject=self.subject(code, domain_key),
                term=self.term,
                school_year=self.year,
                score=Decimal(str(score)),
                status=status,
            )
            for (code, domain_key), score in scores.items()
        ]
        return profile, grades


class FeatureSchemaTests(AcademicDataMixin, TestCase):
    def test_schema_is_the_active_domains_in_order(self):
        schema = load_schema()
        self.assertEqual(schema.keys, tuple(SkillDomain.objects.order_by('sort_order', 'key').values_list('key', flat=True)))
        SkillDomain.objects.filter(key='arts').update(is_active=False)
        smaller = load_schema()
        self.assertNotIn('arts', smaller.keys)
        self.assertNotEqual(schema.version, smaller.version)

    def test_missing_subjects_keep_fixed_dimensions(self):
        _profile, grades = self.student({('gen-math', 'math'): 90})
        features = transform(grades)
        size = len(features.schema.keys)
        self.assertEqual(len(features.values), size)
        self.assertEqual(len(features.observed), size)
        self.assertEqual(features.observed_count, 1)
        space = to_model_space(features.values, features.observed)
        self.assertEqual(len(space), size)
        self.assertTrue(all(value == 0.0 for value, seen in zip(space, features.observed) if not seen))

    def test_invalid_scores_and_unmapped_subjects_are_reported_not_used(self):
        _profile, grades = self.student({('gen-math', 'math'): 88, ('peh', None): 95})
        broken = type('Row', (), {'subject': self.subjects['gen-math'], 'score': '150', 'pk': None})()
        features = transform([*grades, broken])
        self.assertEqual(features.invalid, 1)
        self.assertEqual(features.unmapped, ('peh',))
        self.assertEqual(features.used, 1)
        self.assertEqual(features.value('math'), Decimal('88.00'))

    def test_admin_created_subject_joins_the_vector_without_code_change(self):
        admin = User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/admin/subjects/', {'code': 'robotics', 'name': 'Robotics', 'skill_domain': 'tech'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['skill_domain'], 'tech')
        self.assertEqual(
            client.post('/api/admin/subjects/', {'code': 'x', 'name': 'X', 'skill_domain': 'nope'}).status_code,
            400,
        )
        self.subjects['robotics'] = Subject.objects.get(code='robotics')
        _profile, grades = self.student({('robotics', 'tech'): 93})
        self.assertEqual(transform(grades).value('tech'), Decimal('93.00'))

    def test_seed_maps_research_subjects_and_excludes_peh(self):
        sync_subject_catalog()
        seed_academic_reference()
        seed_matching_exclusions()
        research = set(Subject.objects.filter(skill_domain__key='research').values_list('code', flat=True))
        self.assertEqual(research, {'pr2', 'iii', 'capstone', 'culminating'})
        peh = Subject.objects.get(code='peh')
        self.assertTrue(peh.matching_excluded)
        self.assertIsNone(peh.skill_domain)
        call_command('check_data', stdout=StringIO())

    def test_college_profiles_use_the_same_feature_space(self):
        schema = load_schema()
        for candidate in load_candidates(schema):
            self.assertEqual(len(candidate.vector), len(schema.keys))


class RecommendationTests(AcademicDataMixin, TestCase):
    TECH = {('css', 'tech'): 95, ('prog-java', 'tech'): 87, ('prog-dotnet', 'tech'): 90, ('kasaysayan', 'social'): 90, ('life-career', 'social'): 85, ('mab-kom', 'language'): 80}
    SCIENCE = {('phys-1', 'science'): 93, ('chem-1', 'science'): 91, ('gen-math', 'math'): 88, ('eff-comm', 'language'): 75}
    LANGUAGE = {('eff-comm', 'language'): 92, ('kasaysayan', 'social'): 90, ('gen-math', 'math'): 78, ('gen-sci', 'science'): 74}

    def test_partial_profile_is_not_ranked_on_missing_dimensions(self):
        """Regression: a tech-strong student with no math/science grades once matched Psychology first."""
        _profile, grades = self.student(self.TECH)
        payload = recommend_payload(grades, 'ICTP')
        self.assertTrue(payload['ready'])
        self.assertEqual(strongest_domain(payload['courses'][0]['code']), 'tech')
        features = transform(grades)
        for course in payload['courses']:
            program = CollegeProgram.objects.get(code=course['code'])
            for skill in program.skills.exclude(minimum__isnull=True):
                self.assertIsNotNone(features.value(skill.domain.key))
        self.assertIn('Math', payload['coverage']['needs'])

    def test_different_profiles_change_vector_and_result(self):
        _a, science = self.student(self.SCIENCE)
        _b, language = self.student(self.LANGUAGE)
        self.assertNotEqual(transform(science).values, transform(language).values)
        first = recommend_payload(science)
        second = recommend_payload(language)
        self.assertEqual(strongest_domain(first['courses'][0]['code']), 'science')
        self.assertIn(strongest_domain(second['courses'][0]['code']), ('language', 'social'))
        self.assertNotEqual(first['courses'][0]['code'], second['courses'][0]['code'])

    def test_inactive_college_program_is_never_returned(self):
        _profile, grades = self.student(self.SCIENCE)
        top = recommend_payload(grades)['courses'][0]['code']
        CollegeProgram.objects.filter(code=top).update(is_active=False)
        self.assertNotIn(top, [row['code'] for row in recommend_payload(grades)['courses']])

    def test_too_few_domains_is_not_ready(self):
        _profile, grades = self.student({('gen-math', 'math'): 90, ('phys-1', 'science'): 88})
        payload = recommend_payload(grades)
        self.assertFalse(payload['ready'])
        self.assertEqual(payload['courses'], [])

    def test_payload_identifies_model_and_schema(self):
        _profile, grades = self.student(self.SCIENCE)
        payload = recommend_payload(grades)
        context = RecommendationContext()
        self.assertEqual(payload['model']['feature_schema'], context.schema.version)
        self.assertEqual(payload['model']['catalog'], context.catalog)
        self.assertFalse(payload['model']['trained_on_outcomes'])

    def test_grade_change_is_used_on_next_prediction_without_retraining(self):
        _profile, grades = self.student(self.SCIENCE)
        runs = ModelRun.objects.count()
        before = recommend_payload(grades)
        Grade.objects.filter(pk__in=[row.pk for row in grades], subject__code='phys-1').update(score=Decimal('70'))
        refreshed = list(Grade.objects.filter(pk__in=[row.pk for row in grades]).select_related('subject'))
        after = recommend_payload(refreshed)
        self.assertNotEqual(before['skills'], after['skills'])
        self.assertEqual(ModelRun.objects.count(), runs)

    def test_excluded_and_unmapped_subjects_are_reported_separately(self):
        _profile, grades = self.student({**self.SCIENCE, ('peh', None): 96, ('new-elective', None): 94})
        Subject.objects.filter(code='peh').update(matching_excluded=True)
        features = transform(grades)
        self.assertEqual(features.excluded, ('peh',))
        self.assertEqual(features.unmapped, ('new-elective',))
        self.assertEqual(features.used, len(self.SCIENCE))
        coverage = recommend_payload(grades)['coverage']
        self.assertEqual(coverage['excluded_subjects'], ['peh'])
        self.assertEqual(coverage['unmapped_subjects'], ['new-elective'])
        with self.assertRaisesMessage(CommandError, '1 record(s) need fixing'):
            call_command('check_data', stdout=StringIO())
        Subject.objects.filter(code='new-elective').update(skill_domain=SkillDomain.objects.get(key='arts'))
        call_command('check_data', stdout=StringIO())

    def test_domain_change_in_database_changes_the_vector(self):
        _profile, grades = self.student(self.SCIENCE)
        before = transform(grades)
        Subject.objects.filter(code='phys-1').update(skill_domain=SkillDomain.objects.get(key='tech'))
        after = transform(list(Grade.objects.filter(pk__in=[row.pk for row in grades]).select_related('subject')))
        self.assertIsNone(before.value('tech'))
        self.assertEqual(after.value('tech'), Decimal('93.00'))
        self.assertEqual(after.value('science'), Decimal('91.00'))

    def test_research_subjects_count_through_research(self):
        scores = {(code, 'research'): 90 for code in ('pr2', 'iii', 'capstone', 'culminating')}
        _profile, grades = self.student(scores)
        features = transform(grades)
        self.assertEqual(features.value('research'), Decimal('90.00'))
        self.assertEqual(features.subjects['research'], ['pr2', 'iii', 'capstone', 'culminating'])
        self.assertEqual(features.observed_count, 1)
        self.assertFalse(recommend_payload(grades)['ready'])

    def test_ranking_and_diagnostics_share_one_comparison(self):
        _profile, grades = self.student(self.TECH)
        context = RecommendationContext()
        features = transform(grades, context.schema)
        comparisons = compare_all(features, context.candidates, 'ICTP')
        best = min((row for row in comparisons if row.status == RANKED), key=lambda row: (row.distance, row.candidate.name))
        top = recommend_payload(grades, 'ICTP', context)['courses'][0]
        self.assertEqual(top['code'], best.candidate.code)
        self.assertEqual(top['distance'], round(best.distance, 2))
        self.assertEqual(top['evidence']['observed_domains'], [context.schema.label(key) for key in best.observed])
        self.assertEqual(top['evidence']['status'], best.evidence)
        for row in comparisons:
            self.assertTrue(0.0 <= row.imputed_share <= 1.0)
            self.assertEqual(row.status == NEEDS_DATA, bool(row.missing_minimums))
        unobserved = [index for index, seen in enumerate(features.observed) if not seen]
        self.assertTrue(all(features.values[index] is None for index in unobserved))

    def test_outcome_dataset_uses_only_recorded_outcomes(self):
        self.assertEqual(outcome_dataset(), [])
        profile, grades = self.student(self.SCIENCE)
        CollegeOutcome.objects.create(
            student=profile,
            college_program=CollegeProgram.objects.get(code='bsbio'),
            school_year=self.year,
        )
        rows = outcome_dataset()
        self.assertEqual([(row['student'], row['label']) for row in rows], [(profile.pk, 'bsbio')])
        self.assertEqual(len(rows[0]['vector']), len(load_schema().keys))
        self.assertFalse(recommend_payload(grades)['model']['trained_on_outcomes'])


class EvidenceCoverageTests(AcademicDataMixin, TestCase):
    """Evidence is separate from similarity: how much of a program's profile has real grades behind it."""

    BASE = {('css', 'tech'): 90, ('eff-comm', 'language'): 85, ('kasaysayan', 'social'): 88}

    def program(self, code, levels, minimums=None):
        college = CollegeProgram.objects.create(code=code, name=code.upper())
        for key, level in levels.items():
            CollegeProgramSkill.objects.create(
                college_program=college,
                domain=SkillDomain.objects.get(key=key),
                level=Decimal(level),
                minimum=Decimal((minimums or {})[key]) if key in (minimums or {}) else None,
            )
        return college

    def comparison(self, grades, code):
        context = RecommendationContext()
        features = transform(grades, context.schema)
        return next(row for row in compare_all(features, context.candidates) if row.candidate.code == code)

    def shown(self, grades):
        context = RecommendationContext()
        ranking = rank(transform(grades, context.schema), context.candidates, limit=None)
        return {row['code']: row for row in ranking.courses}

    def test_rank_returns_a_named_result_that_its_caller_reads_by_field(self):
        """Regression: the caller once unpacked two values from a three-value rank()."""
        _profile, grades = self.student(self.BASE)
        context = RecommendationContext()
        ranking = rank(transform(grades, context.schema), context.candidates)
        self.assertIsInstance(ranking, Ranking)
        self.assertEqual(Ranking._fields, ('courses', 'blocked', 'not_evaluated'))
        payload = recommend_payload(grades, None, context)
        self.assertEqual(payload['courses'], ranking.courses)
        self.assertEqual(payload['coverage']['not_evaluated'], ranking.not_evaluated)
        self.assertEqual(payload['coverage']['needs'], [context.schema.label(key) for key, _n in ranking.blocked.most_common()])

    def test_full_coverage_is_strong(self):
        self.program('full3', {'math': 85, 'science': 85, 'language': 80}, {'math': 80})
        _profile, grades = self.student({('gen-math', 'math'): 90, ('phys-1', 'science'): 88, ('eff-comm', 'language'): 82})
        row = self.comparison(grades, 'full3')
        self.assertEqual((len(row.observed), row.total, row.coverage), (3, 3, 1.0))
        self.assertEqual(row.minimum_status, {'math': PASSED})
        self.assertEqual(row.evidence, STRONG)
        self.assertTrue(row.eligible)
        self.assertEqual(self.shown(grades)['full3']['evidence']['status'], STRONG)

    def test_partial_coverage_is_limited_not_strong(self):
        self.program('part3', {'tech': 86, 'math': 72, 'service': 75}, {'tech': 78})
        _profile, grades = self.student(self.BASE)
        row = self.comparison(grades, 'part3')
        self.assertEqual((len(row.observed), row.total), (1, 3))
        self.assertEqual(round(100 * row.coverage, 2), 33.33)
        self.assertEqual(row.evidence, LIMITED)
        self.assertTrue(row.eligible)
        evidence = self.shown(grades)['part3']['evidence']
        self.assertEqual((evidence['status'], evidence['observed'], evidence['total'], evidence['coverage']), (LIMITED, 1, 3, 33.33))

    def test_threshold_is_one_setting(self):
        self.program('part3', {'tech': 86, 'math': 72, 'service': 75}, {'tech': 78})
        _profile, grades = self.student(self.BASE)
        before = self.comparison(grades, 'part3')
        with override_settings(MIN_RECOMMENDATION_EVIDENCE_COVERAGE=0.3):
            after = self.comparison(grades, 'part3')
            self.assertEqual(recommend_payload(grades)['coverage']['threshold'], 0.3)
        self.assertEqual((before.evidence, after.evidence), (LIMITED, STRONG))
        self.assertEqual(before.distance, after.distance)

    def test_zero_coverage_is_insufficient_and_not_shown(self):
        self.program('zero2', {'arts': 85, 'business': 80})
        _profile, grades = self.student(self.BASE)
        row = self.comparison(grades, 'zero2')
        self.assertEqual((row.coverage, row.evidence, row.eligible), (0.0, INSUFFICIENT, False))
        self.assertNotIn('zero2', self.shown(grades))
        self.assertIn('Arts', recommend_payload(grades)['coverage']['needs'])

    def test_minimum_without_a_grade_is_unknown_not_passed(self):
        self.program('needmath', {'math': 90, 'tech': 80}, {'math': 85})
        _profile, grades = self.student(self.BASE)
        row = self.comparison(grades, 'needmath')
        self.assertEqual(row.minimum_status, {'math': UNKNOWN})
        self.assertEqual((row.status, row.evidence, row.eligible), (NEEDS_DATA, INSUFFICIENT, False))
        self.assertNotIn('needmath', self.shown(grades))
        payload = recommend_payload(grades)
        self.assertIn('Math', payload['coverage']['needs'])
        self.assertGreaterEqual(payload['coverage']['not_evaluated'], 1)

    def test_known_minimum_that_fails_is_failed(self):
        self.program('hightech', {'tech': 95, 'language': 80}, {'tech': 95})
        _profile, grades = self.student(self.BASE)
        row = self.comparison(grades, 'hightech')
        self.assertEqual(row.minimum_status, {'tech': FAILED})
        self.assertEqual(row.status, BELOW_MINIMUM)
        self.assertFalse(row.eligible)

    def test_peh_grade_does_not_add_evidence(self):
        _profile, grades = self.student(self.BASE)
        before = {row.candidate.code: (row.observed, row.evidence) for row in compare_all(transform(grades), load_candidates(load_schema()))}
        _other, with_peh = self.student({**self.BASE, ('peh', None): 99})
        Subject.objects.filter(code='peh').update(matching_excluded=True)
        features = transform(with_peh)
        after = {row.candidate.code: (row.observed, row.evidence) for row in compare_all(features, load_candidates(load_schema()))}
        self.assertEqual(features.excluded, ('peh',))
        self.assertEqual(before, after)

    def test_research_subjects_add_research_coverage(self):
        science = {('phys-1', 'science'): 92, ('gen-math', 'math'): 88, ('eff-comm', 'language'): 80}
        _profile, grades = self.student(science)
        without = self.comparison(grades, 'bsbio')
        research = {(code, 'research'): 90 for code in ('pr2', 'iii', 'capstone', 'culminating')}
        _other, more = self.student({**science, **research})
        with_research = self.comparison(more, 'bsbio')
        self.assertNotIn('research', without.observed)
        self.assertIn('research', with_research.observed)
        self.assertEqual(len(with_research.observed), len(without.observed) + 1)
        self.assertEqual(with_research.coverage, 1.0)

    def test_missing_domains_stay_missing(self):
        _profile, grades = self.student(self.BASE)
        features = transform(grades)
        payload = recommend_payload(grades)
        for key, value, seen in zip(features.schema.keys, features.values, features.observed):
            self.assertEqual(value is None, not seen, key)
        self.assertEqual({row['key'] for row in payload['skills']}, {'tech', 'language', 'social'})
        space = to_model_space(features.values, features.observed)
        self.assertTrue(all(value == 0.0 for value, seen in zip(space, features.observed) if not seen))
        self.assertEqual(CollegeOutcome.objects.count(), 0)
        self.assertFalse(payload['model']['trained_on_outcomes'])


class ScreenshotStudentTests(TestCase):
    """The student shown in the UI: three tech subjects, two social, one language, in ICTP."""

    GRADES = {'prog-dotnet': 90, 'prog-java': 80, 'css': 90, 'life-career': 95, 'mab-kom': 99, 'kasaysayan': 96}
    NAMED = {'bsindtech': (1, 3), 'bsed': (2, 5), 'bacom': (2, 6)}

    def setUp(self):
        seed_programs()
        sync_subject_catalog()
        seed_academic_reference()
        seed_matching_exclusions()
        seed_college_programs()
        year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        term = Term.objects.create(school_year=year, number=1, label='Term 1')
        user = User.objects.create_user(email='learner@example.com', password='Strongpass1', role=User.Role.STUDENT)
        profile = StudentProfile.objects.create(user=user, lrn='136000000004')
        self.grades = [
            Grade.objects.create(
                student=profile,
                subject=Subject.objects.get(code=code),
                term=term,
                school_year=year,
                score=Decimal(score),
                status=Grade.Status.RELEASED,
            )
            for code, score in self.GRADES.items()
        ]
        self.context = RecommendationContext()
        self.features = transform(self.grades, self.context.schema)

    def expected_distance(self, code):
        """The same number worked out independently from the database rows."""
        keys = self.context.schema.keys
        seen = {key: float(value) for key, value in self.features.averages().items()}
        mean = sum(seen.values()) / len(seen)
        college = CollegeProgram.objects.get(code=code)
        levels = {row.domain.key: float(row.level) for row in college.skills.all()}
        level_mean = sum(levels.values()) / len(levels)
        total = sum(
            ((seen[key] - mean if key in seen else 0.0) - (levels[key] - level_mean if key in levels else 0.0)) ** 2
            for key in keys
        )
        boost = TRACK_BOOST if college.shs_programs.filter(code='ICTP').exists() else 1
        return math.sqrt(total / len(keys)) * boost

    def test_feature_values(self):
        self.assertEqual(self.features.value('tech'), Decimal('86.67'))
        self.assertEqual(self.features.value('language'), Decimal('99.00'))
        self.assertEqual(self.features.value('social'), Decimal('95.50'))
        self.assertEqual(self.features.observed_count, 3)
        self.assertEqual((self.features.used, self.features.excluded, self.features.unmapped), (6, (), ()))

    def test_named_programs_have_limited_evidence_and_the_documented_distance(self):
        rows = {row.candidate.code: row for row in compare_all(self.features, self.context.candidates, 'ICTP')}
        for code, (observed, total) in self.NAMED.items():
            row = rows[code]
            self.assertEqual((len(row.observed), row.total), (observed, total), code)
            self.assertEqual(row.evidence, LIMITED, code)
            self.assertTrue(row.eligible, code)
            self.assertNotIn(UNKNOWN, row.minimum_status.values(), code)
            self.assertAlmostEqual(row.distance, self.expected_distance(code), places=6, msg=code)
        self.assertEqual(rows['bsindtech'].observed, ('tech',))
        self.assertTrue(rows['bsindtech'].track_match)
        self.assertFalse(rows['bsed'].track_match)

    def test_order_follows_distance_and_evidence_is_reported(self):
        payload = recommend_payload(self.grades, 'ICTP', self.context)
        rows = compare_all(self.features, self.context.candidates, 'ICTP')
        by_distance = sorted((row for row in rows if row.eligible), key=lambda row: (row.distance, row.candidate.name))
        self.assertEqual([row['code'] for row in payload['courses']], [row.candidate.code for row in by_distance[:3]])
        self.assertTrue(payload['ready'])
        self.assertEqual(payload['evidence'], LIMITED)
        self.assertTrue(payload['summary'].startswith('Closest so far:'))
        self.assertNotIn('match', payload['courses'][0]['reason'])
        self.assertEqual(payload['coverage']['not_evaluated'], sum(1 for row in rows if row.evidence == INSUFFICIENT))
        for row in rows:
            if UNKNOWN in row.minimum_status.values():
                self.assertFalse(row.eligible, row.candidate.code)


class CurriculumTransitionTests(TestCase):
    def setUp(self):
        self.k12 = Curriculum.objects.get(code='k12-shs')
        self.sshs = Curriculum.objects.get(code='strengthened-shs')
        self.old_year = SchoolYear.objects.create(label='2025-2026')
        self.new_year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.old_stem = Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12', curriculum=self.k12)
        self.stemc = Program.objects.create(
            code='STEMC', name='STEM Cluster', grade_level='Grade 11', curriculum=self.sshs, continues_to=self.old_stem
        )

    def test_transition_year_resolves_each_grade_separately(self):
        self.assertEqual(curriculum_for(self.old_year, 'Grade 11'), self.sshs)
        self.assertEqual(curriculum_for(self.old_year, 'Grade 12'), self.k12)

    def test_future_year_moves_grade12_without_rewriting_history(self):
        freeze_year(self.old_year)
        new_stem = Program.objects.create(code='STEM-S', name='STEM (SSHS)', grade_level='Grade 12', curriculum=self.sshs)
        self.old_stem.is_active = False
        self.old_stem.save(update_fields=['is_active'])
        self.assertEqual(curriculum_for(self.new_year, 'Grade 12'), self.sshs)
        self.assertEqual(list(programs_for(self.new_year, 'Grade 12')), [new_stem])
        self.assertEqual(curriculum_for(self.old_year, 'Grade 12'), self.k12)

    def test_new_year_carries_forward_and_can_switch(self):
        head = User.objects.create_user(email='head@dampol1nhs.edu.ph', password='Strongpass1', role=User.Role.HEAD_TEACHER)
        client = APIClient()
        client.force_authenticate(user=head)
        freeze_year(self.new_year)
        created = client.post('/api/school-years/', {'label': '2027-2028'}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['curricula'], {'Grade 11': 'strengthened-shs', 'Grade 12': 'k12-shs'})
        switched = client.patch(
            f"/api/school-years/{created.data['id']}/",
            {'curricula': {'Grade 12': 'strengthened-shs'}},
            format='json',
        )
        self.assertEqual(switched.status_code, 200, switched.data)
        self.assertEqual(switched.data['curricula']['Grade 12'], 'strengthened-shs')
        self.assertEqual(curriculum_for(self.new_year, 'Grade 12'), self.k12)
        bad = client.patch(f"/api/school-years/{created.data['id']}/", {'curricula': {'Grade 12': 'nope'}}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_continuation_must_point_to_grade12(self):
        admin = User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(user=admin)
        bad = client.patch(f'/api/admin/programs/{self.stemc.pk}/', {'continues_to': self.stemc.pk}, format='json')
        self.assertEqual(bad.status_code, 400)
        good = client.patch(f'/api/admin/programs/{self.stemc.pk}/', {'continues_to': self.old_stem.pk}, format='json')
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.data['curriculum'], 'strengthened-shs')


class ForecastModelTests(TestCase):
    def setUp(self):
        self.sshs = Curriculum.objects.get(code='strengthened-shs')
        k12 = Curriculum.objects.get(code='k12-shs')
        stem = Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12', curriculum=k12, sort_order=1)
        self.stemc = Program.objects.create(
            code='STEMC', name='STEM Cluster', grade_level='Grade 11', curriculum=self.sshs, continues_to=stem, sort_order=13
        )
        self.admin = User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        self._serial = 0

    def year(self, label, applied, approved, current=False):
        """A non-current year is a completed (archived) year, the only kind training uses."""
        year = SchoolYear.objects.create(label=label, is_current=current, archived_at=None if current else timezone.now())
        for index in range(applied):
            self._serial += 1
            user = User.objects.create_user(email=f'r{self._serial}@example.com', password='Strongpass1', role=User.Role.STUDENT)
            Registration.objects.create(
                user=user,
                school_year=year,
                program=self.stemc,
                grade_level_enrollment='Grade 11',
                status=Registration.Status.APPROVED if index < approved else Registration.Status.PENDING,
            )
        return year

    def test_counts_come_from_registrations(self):
        year = self.year('2025-2026', applied=5, approved=3, current=True)
        payload = build_grade11_forecast(year)
        row = next(item for item in payload['clusters'] if item['code'] == 'STEMC')
        registrations = Registration.objects.filter(school_year=year, program=self.stemc)
        self.assertEqual(row['applied'], registrations.exclude(status=Registration.Status.REJECTED).count())
        self.assertEqual(row['count'], registrations.filter(status=Registration.Status.APPROVED).count())
        self.assertEqual(payload['strands'][0]['code'], 'STEM')
        self.assertEqual(payload['strands'][0]['basis'], 'estimated')

    def test_new_grade11_program_appears_without_code_change(self):
        year = self.year('2025-2026', applied=1, approved=1, current=True)
        Program.objects.create(code='AGRI', name='Agri-Fishery', grade_level='Grade 11', curriculum=self.sshs)
        self.assertIn('AGRI', [row['code'] for row in build_grade11_forecast(year)['clusters']])

    def test_one_year_is_not_ready(self):
        self.year('2025-2026', applied=2, approved=2, current=True)
        run = train_forecast()
        self.assertFalse(run.metrics['ready'])
        payload = attach_attractiveness(build_grade11_forecast())
        self.assertEqual(payload['method'], 'counts')
        self.assertTrue(payload['ready_reason'])

    def test_three_completed_years_train_regression(self):
        self.year('2022-2023', 2, 2)
        self.year('2023-2024', 3, 3)
        self.year('2024-2025', 4, 4)
        self.year('2025-2026', 1, 1, current=True)
        run = train_forecast()
        self.assertTrue(run.metrics['ready'])
        self.assertEqual(run.feature_schema, FEATURE_SCHEMA)
        self.assertEqual(run.curriculum_scope, ['strengthened-shs'])
        self.assertFalse(run.metrics['evaluation']['evaluated'])
        payload = attach_attractiveness(build_grade11_forecast())
        stemc = next(row for row in payload['clusters'] if row['code'] == 'STEMC')
        self.assertEqual(payload['method'], 'linear_regression')
        self.assertEqual(stemc['projected'], 6)
        self.assertEqual(stemc['projected_basis'], 'forecast')
        self.assertEqual(stemc['next_intake'], 6)
        self.assertEqual(payload['model']['version'], run.version)

    def test_year_still_enrolling_is_not_trained_on(self):
        self.year('2023-2024', 3, 3)
        self.year('2024-2025', 4, 4)
        self.year('2025-2026', 1, 1, current=True)
        run = train_forecast()
        self.assertFalse(run.metrics['ready'])
        stemc = next(row for row in attach_attractiveness(build_grade11_forecast())['clusters'] if row['code'] == 'STEMC')
        self.assertEqual(stemc['next_intake'], 1)
        self.assertEqual(stemc['next_intake_basis'], 'estimate')

    def test_four_years_reports_held_out_error(self):
        counts = [(2022, 2), (2023, 4), (2024, 5), (2025, 9), (2026, 1)]
        for start, applied in counts:
            self.year(f'{start}-{start + 1}', applied, applied, current=start == 2026)
        evaluation = train_forecast().metrics['evaluation']
        model = fit_line([0, 1, 2], [2, 4, 5])
        error = predict_line(model, 3) - 9
        self.assertTrue(evaluation['evaluated'])
        self.assertAlmostEqual(evaluation['mae'], round(abs(error), 3))
        self.assertAlmostEqual(evaluation['rmse'], round(math.sqrt(error**2), 3))

    def test_years_under_another_curriculum_are_not_used(self):
        years = [self.year(f'{start}-{start + 1}', 3, 3, current=start == 2025) for start in (2022, 2023, 2024, 2025)]
        SchoolYearCurriculum.objects.create(
            school_year=years[0],
            grade_level='Grade 11',
            curriculum=Curriculum.objects.get(code='k12-shs'),
        )
        run = train_forecast()
        self.assertFalse(run.metrics['ready'])
        snapshot = ClusterSnapshot.objects.get(school_year=years[0], program=self.stemc)
        self.assertEqual(snapshot.curriculum.code, 'k12-shs')
        self.assertEqual(snapshot_year(years[0])[0].curriculum.code, 'k12-shs')

    def test_plan_counts_sections_and_flags_old_curriculum(self):
        year = self.year('2025-2026', applied=4, approved=3, current=True)
        section = Section.objects.create(school_year=year, name='STEMC-A', grade_level='Grade 11', program=self.stemc, capacity=2)
        placed = StudentProfile.objects.create(user=User.objects.get(email='r1@example.com'), lrn='136000000001')
        StudentSection.objects.create(student=placed, section=section, school_year=year)
        payload = attach_attractiveness(build_grade11_forecast(year))
        stemc = next(row for row in payload['clusters'] if row['code'] == 'STEMC')
        self.assertEqual((stemc['placed'], stemc['capacity'], stemc['share'], stemc['rank']), (1, 2, 100, 1))
        self.assertEqual(payload['typical_capacity'], 2)
        self.assertEqual(stemc['sections_needed'], 2)
        strand = payload['strands'][0]
        self.assertEqual((strand['code'], strand['count'], strand['sections_needed']), ('STEM', 3, 2))
        self.assertFalse(strand['ready'])
        self.assertTrue(any('STEMC leads to STEM' in item for item in payload['plan']['warnings']))

        new_stem = Program.objects.create(code='STEM-S', name='STEM (SSHS)', grade_level='Grade 12', curriculum=self.sshs)
        self.stemc.continues_to = new_stem
        self.stemc.save(update_fields=['continues_to'])
        payload = build_grade11_forecast(year)
        self.assertTrue(payload['strands'][0]['ready'])
        self.assertEqual(payload['plan']['warnings'], [])

    def test_forecast_request_does_not_train_or_write(self):
        self.year('2025-2026', 2, 1, current=True)
        client = APIClient()
        client.force_authenticate(user=self.admin)
        before = (ModelRun.objects.count(), ClusterSnapshot.objects.count())
        self.assertEqual(client.get('/api/admin/forecast/').status_code, 200)
        self.assertEqual((ModelRun.objects.count(), ClusterSnapshot.objects.count()), before)

    def test_outdated_artifact_is_not_used(self):
        self.year('2025-2026', 2, 2, current=True)
        save_run(name='forecast', algorithm='linear_regression', n_train=0, n_test=0, metrics={'ready': True}, artifact={'models': {}, 'next_index': 1})
        payload = attach_attractiveness(build_grade11_forecast())
        self.assertEqual(payload['method'], 'counts')
        self.assertIn('older format', payload['ready_reason'])
        self.assertIsNone(payload['model'])


class IntentModelTests(TestCase):
    def setUp(self):
        FaqEntry.objects.create(
            topic='registration',
            keywords='register, sign up',
            question='How do I register?',
            answer='Open Register and submit the form.',
        )

    def test_classifies_registration(self):
        train_intent()
        topic, confidence = classify_question('How do I register?')
        self.assertEqual(topic, 'registration')
        self.assertGreater(confidence, 0.4)

    def test_seed_faqs_is_idempotent(self):
        created = seed_faqs()
        self.assertGreaterEqual(created, 30)
        self.assertEqual(seed_faqs(), 0)

    def test_matching_faq_returns_the_relevant_answer(self):
        FaqEntry.objects.create(
            topic='login',
            keywords='forgot password, reset password, change password',
            question='How do I reset a forgotten password?',
            answer='Use the password reset flow.',
        )
        FaqEntry.objects.create(
            topic='login',
            keywords='sign in, login, lrn',
            question='How do I log in?',
            answer='Students use their LRN to sign in.',
        )
        self.assertEqual(
            matching_faq_answer('Where can I reset my password?', 'login'),
            'Use the password reset flow.',
        )

    def test_chatbot_uses_trained_topic(self):
        train_intent()
        response = APIClient().post('/api/chatbot/', {'question': 'How do I sign up?'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['topic'], 'registration')
        self.assertIn('Register', response.data['answer'])

    def test_request_never_trains(self):
        response = APIClient().post('/api/chatbot/', {'question': 'How do I register?'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['topic'], 'other')
        self.assertIsNone(last_run('intent'))

    def test_faq_topic_outside_the_seed_list_is_learned(self):
        FaqEntry.objects.create(
            topic='library',
            keywords='library, books, borrow books, library hours, librarian',
            question='When is the library open?',
            answer='The library is open on school days.',
        )
        run = train_intent()
        self.assertIn('library', run.metrics['topics'])
        self.assertIn('library', run.artifact['model']['classes'])

    def test_program_answer_lists_live_programs(self):
        SchoolYear.objects.create(label='2025-2026', is_current=True)
        sshs = Curriculum.objects.get(code='strengthened-shs')
        Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11', curriculum=sshs)
        Program.objects.create(code='OLDX', name='Retired', grade_level='Grade 11', curriculum=sshs, is_active=False)
        FaqEntry.objects.create(topic='programs', keywords='program', question='Programs?', answer='See the Programs page.')
        answers = answers_for('programs')
        self.assertIn('STEMC - STEM Cluster', answers[0])
        self.assertIn(sshs.name, answers[0])
        self.assertNotIn('OLDX', answers[0])
        self.assertEqual(answers[1], 'See the Programs page.')

    def test_assistant_is_admin_only(self):
        train_intent()
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


class ModelUpkeepTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        self.head = User.objects.create_user(email='head@dampol1nhs.edu.ph', password='Strongpass1', role=User.Role.HEAD_TEACHER)
        FaqEntry.objects.create(topic='registration', keywords='register, sign up', question='How do I register?', answer='Open Register.')

    def test_archiving_a_year_retrains_the_forecast(self):
        SchoolYear.objects.create(label='2026-2027', is_current=True)
        old = SchoolYear.objects.create(label='2025-2026')
        client = APIClient()
        client.force_authenticate(user=self.head)
        self.assertEqual(client.post(f'/api/school-years/{old.pk}/archive/').status_code, 200)
        run = last_run('forecast')
        self.assertEqual(run.dataset['completed_years'], ['2025-2026'])
        self.assertFalse(forecast_is_stale(run))
        SchoolYear.objects.filter(pk=old.pk).update(archived_at=None)
        self.assertTrue(forecast_is_stale(run))

    def test_admin_can_retrain_both_models(self):
        SchoolYear.objects.create(label='2025-2026', is_current=True)
        client = APIClient()
        client.force_authenticate(user=self.admin)
        forecast = client.post('/api/admin/forecast/')
        self.assertEqual(forecast.status_code, 200)
        self.assertFalse(forecast.data['model']['stale'])
        assistant = client.post('/api/ml/assistant/')
        self.assertEqual(assistant.status_code, 200)
        self.assertTrue(assistant.data['intent']['ready'])
        self.assertFalse(assistant.data['intent']['stale'])

    def test_faq_edit_in_admin_retrains_the_chatbot(self):
        train_intent()
        entry = FaqEntry.objects.get()
        entry.keywords = 'register, sign up, enroll online'
        entry.save()
        self.assertTrue(intent_is_stale(last_run('intent')))
        request = RequestFactory().post('/admin/')
        request.user = self.admin
        request.session = {}
        request._messages = FallbackStorage(request)
        FaqEntryAdmin(FaqEntry, admin.site).save_model(request, entry, None, True)
        self.assertFalse(intent_is_stale(last_run('intent')))

    def test_old_runs_are_pruned(self):
        for _index in range(KEEP_RUNS + 3):
            save_run(name='forecast', algorithm='linear_regression', n_train=0, n_test=0, metrics={}, artifact={})
        runs = ModelRun.objects.filter(name='forecast')
        self.assertEqual(runs.count(), KEEP_RUNS)
        self.assertEqual(runs.first().version, KEEP_RUNS + 3)
