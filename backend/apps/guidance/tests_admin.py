"""Admin maintenance: catalog rules, imports, expert ratings, the interest map, the instrument and settings."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.access.models import AccessRequest, AccessTag
from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.guidance.catalog import IMPORTANCE, MIN_RATERS
from apps.guidance.models import InterestInstrument
from apps.guidance.testing import GuidanceFixture
from apps.ml.models import (
    CollegeProgram,
    CollegeProgramSkill,
    FamilyInterestMap,
    ProgramProfileSnapshot,
    ProgramSkillRating,
    RecommenderConfig,
)
from apps.ml.recommender_config import DEFAULTS
from apps.school.models import SkillDomain

CSV_HEADER = 'code,name,abbreviation,family,description,career_overview,source,source_url,verified_on\n'


class AdminOnlyTests(GuidanceFixture, TestCase):
    def test_admin_endpoints_refuse_teachers_and_students(self):
        student = self.make_student()
        urls = [
            '/api/guidance/admin/catalog/',
            '/api/guidance/admin/instruments/',
            '/api/guidance/admin/outcomes/',
            '/api/guidance/admin/recommender/',
            '/api/guidance/admin/config/',
        ]
        for user in (self.adviser, student.user):
            client = self.client_for(user)
            for url in urls:
                self.assertEqual(client.get(url).status_code, 403, (user.role, url))
            self.assertEqual(client.post('/api/guidance/admin/programs/', {'code': 'x'}, format='json').status_code, 403)


class CatalogTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.client = self.client_for(self.admin)

    def create(self, code='bsds', **extra):
        return self.client.post(
            '/api/guidance/admin/programs/',
            {'code': code, 'name': 'BS Data Science', 'family': 'computing', **extra},
            format='json',
        )

    def test_a_new_program_starts_switched_off_and_is_audited(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        program = CollegeProgram.objects.get(code='bsds')
        self.assertFalse(program.is_active)
        self.assertTrue(AuditLog.objects.filter(action='college_program_added').exists())

    def test_program_cannot_switch_on_without_source_and_validated_profile(self):
        self.create()
        refused = self.client.patch('/api/guidance/admin/programs/bsds/', {'is_active': True}, format='json')
        self.assertEqual(refused.status_code, 400)
        self.assertIn('verified authoritative source', str(refused.data))
        self.client.post(
            '/api/guidance/admin/programs/bsds/verify/',
            {'source': 'CHED CMO No. 25, s. 2015', 'verified_on': '2026-09-01'},
            format='json',
        )
        still = self.client.patch('/api/guidance/admin/programs/bsds/', {'is_active': True}, format='json')
        self.assertEqual(still.status_code, 400)
        CollegeProgram.objects.filter(code='bsds').update(profile_status=CollegeProgram.ProfileStatus.VALIDATED)
        ok = self.client.patch('/api/guidance/admin/programs/bsds/', {'is_active': True}, format='json')
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertTrue(CollegeProgram.objects.get(code='bsds').is_active)

    def test_input_is_validated_server_side(self):
        self.assertEqual(self.create(code='Bad Code').status_code, 400)
        self.assertEqual(self.create(code='bsx', family='no-family').status_code, 400)
        self.create()
        future = self.client.post('/api/guidance/admin/programs/bsds/verify/', {'source': 'x', 'verified_on': '2999-01-01'}, format='json')
        self.assertEqual(future.status_code, 400)
        bad_url = self.client.patch('/api/guidance/admin/programs/bsds/', {'source_url': 'javascript:alert(1)'}, format='json')
        self.assertEqual(bad_url.status_code, 400)

    def test_official_requirement_always_keeps_its_source(self):
        response = self.client.post(
            '/api/guidance/admin/programs/bscs/requirement/',
            {'domain': 'math', 'official': True, 'minimum': 85},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            '/api/guidance/admin/programs/bscs/requirement/',
            {'domain': 'math', 'official': True, 'minimum': 85, 'source': 'University admission policy 2026'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        skill = CollegeProgramSkill.objects.get(college_program__code='bscs', domain__key='math')
        self.assertEqual(skill.minimum_kind, CollegeProgramSkill.MinimumKind.OFFICIAL)
        self.assertTrue(ProgramProfileSnapshot.objects.filter(college_program__code='bscs').exists())

    def test_strand_pathways_are_edited_as_context(self):
        response = self.client.patch('/api/guidance/admin/programs/bsit/', {'shs_programs': ['ICTP']}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['program']['shs_programs'], ['ICTP'])
        self.assertEqual(self.client.patch('/api/guidance/admin/programs/bsit/', {'shs_programs': ['NOPE']}, format='json').status_code, 400)

    def test_csv_import_previews_rejects_malformed_rows_and_commits_clean_files(self):
        bad = SimpleUploadedFile('c.csv', (CSV_HEADER + 'BAD CODE,,,computing,,,,,\nbsds,BS Data Science,,nope,,,,,\n').encode())
        preview = self.client.post('/api/guidance/admin/programs/import/', {'file': bad}, format='multipart')
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data['errors'], 2)
        self.assertFalse(CollegeProgram.objects.filter(code='bsds').exists())
        unknown = SimpleUploadedFile('c.csv', b'code,name,family,evil\nx,y,computing,1\n')
        self.assertEqual(self.client.post('/api/guidance/admin/programs/import/', {'file': unknown}, format='multipart').status_code, 400)
        good = SimpleUploadedFile('c.csv', (CSV_HEADER + 'bsds,BS Data Science,BSDS,computing,Data work,,,,\n').encode())
        committed = self.client.post('/api/guidance/admin/programs/import/', {'file': good, 'commit': 'true'}, format='multipart')
        self.assertEqual(committed.status_code, 200, committed.data)
        program = CollegeProgram.objects.get(code='bsds')
        self.assertEqual((program.abbreviation, program.is_active), ('BSDS', False))

    def test_interest_map_is_validated_and_saved(self):
        self.assertEqual(self.client.put('/api/guidance/admin/interest-map/', {'map': {'computing': ['X']}}, format='json').status_code, 400)
        self.assertEqual(self.client.put('/api/guidance/admin/interest-map/', {'map': {'computing': []}}, format='json').status_code, 400)
        response = self.client.put('/api/guidance/admin/interest-map/', {'map': {'computing': ['C', 'I']}}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(FamilyInterestMap.objects.filter(family__code='computing').order_by('riasec').values_list('riasec', flat=True)),
            ['C', 'I'],
        )


class ExpertRatingTests(GuidanceFixture, TestCase):
    """A tagged teacher's ratings go through the Admin's approval, then the Admin applies the median."""

    def setUp(self):
        super().setUp()
        self.raters = [self.make_user(User.Role.TEACHER, f'rater{index}') for index in range(MIN_RATERS)]
        for rater in self.raters:
            AccessTag.objects.create(activity='rate_programs', holder=rater, granted_by=self.admin)
        self.domains = list(SkillDomain.objects.filter(is_active=True).order_by('sort_order', 'key').values_list('key', flat=True))

    def ratings_for(self, tech_importance, other='typical'):
        rows = []
        for domain in self.domains:
            rows.append({'domain': domain, 'importance': tech_importance if domain == 'tech' else other})
        return rows

    def submit_and_approve(self, rater, tech_importance, other='typical'):
        client = self.client_for(rater)
        response = client.post(
            '/api/access/requests/',
            {
                'activity': 'rate_programs',
                'payload': {'program': 'bsit', 'ratings': self.ratings_for(tech_importance, other)},
                'note': 'Rated from the CHED program standard.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        request = AccessRequest.objects.filter(requested_by=rater).latest('id')
        decided = self.client_for(self.admin).post(f'/api/access/requests/{request.pk}/decide/', {'approve': True, 'note': 'ok'}, format='json')
        self.assertEqual(decided.status_code, 200, decided.data)

    def test_rating_form_hides_current_profile_numbers(self):
        data = self.client_for(self.raters[0]).get('/api/guidance/ratings/').data
        bsit = next(row for row in data['programs'] if row['code'] == 'bsit')
        self.assertNotIn('profile', bsit)
        self.assertEqual(len(data['importance']), 5)
        self.assertEqual(self.client_for(self.make_student().user).get('/api/guidance/ratings/').status_code, 403)

    def test_median_of_approved_ratings_becomes_the_validated_profile(self):
        admin = self.client_for(self.admin)
        self.submit_and_approve(self.raters[0], 'more')
        early = admin.post('/api/guidance/admin/programs/bsit/apply-ratings/', {'source': 'CHED PSG for BSIT'}, format='json')
        self.assertEqual(early.status_code, 400)
        self.submit_and_approve(self.raters[1], 'more')
        self.submit_and_approve(self.raters[2], 'more')
        self.assertEqual(ProgramSkillRating.objects.filter(college_program__code='bsit').count(), MIN_RATERS * len(self.domains))
        applied = admin.post('/api/guidance/admin/programs/bsit/apply-ratings/', {'source': 'CHED PSG for BSIT'}, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        program = CollegeProgram.objects.get(code='bsit')
        self.assertEqual((program.profile_status, program.profile_version), (CollegeProgram.ProfileStatus.VALIDATED, 2))
        tech = program.skills.get(domain__key='tech')
        self.assertEqual((tech.level, tech.minimum), (IMPORTANCE['more'], None))
        snapshot = ProgramProfileSnapshot.objects.get(college_program=program, version=2)
        self.assertEqual(len(snapshot.validators), MIN_RATERS)
        self.assertEqual(snapshot.source, 'CHED PSG for BSIT')

    def test_disagreement_blocks_apply_and_identical_resubmit(self):
        self.submit_and_approve(self.raters[0], 'much_more')
        self.submit_and_approve(self.raters[1], 'typical')
        self.submit_and_approve(self.raters[2], 'typical')
        blocked = self.client_for(self.admin).post(
            '/api/guidance/admin/programs/bsit/apply-ratings/', {'source': 'CHED PSG for BSIT'}, format='json'
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('disagree', str(blocked.data).lower())
        repeat = self.client_for(self.raters[0]).post(
            '/api/access/requests/',
            {
                'activity': 'rate_programs',
                'payload': {'program': 'bsit', 'ratings': self.ratings_for('much_more')},
                'note': 'same again',
            },
            format='json',
        )
        self.assertEqual(repeat.status_code, 400)

    def test_invalid_ratings_are_rejected(self):
        client = self.client_for(self.raters[0])
        for ratings in ([], [{'domain': 'tech', 'importance': 'typical'}], [{'domain': 'nope', 'importance': 'typical'}]):
            response = client.post(
                '/api/access/requests/',
                {'activity': 'rate_programs', 'payload': {'program': 'bsit', 'ratings': ratings}, 'note': 'x'},
                format='json',
            )
            self.assertEqual(response.status_code, 400, ratings)


class InstrumentAndConfigTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.client = self.client_for(self.admin)

    def test_activation_requires_license_confirmation(self):
        newer = InterestInstrument.objects.create(code='onet-mini-ip', version=3, name='v3', source='x', attribution='y')
        response = self.client.post(f'/api/guidance/admin/instruments/{newer.pk}/activate/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InterestInstrument.objects.filter(active_marker='active').get(), self.instrument)

    def test_settings_are_validated_versioned_and_only_one_is_active(self):
        bad = {**DEFAULTS, 'academic_tiers': {'strong': 9, 'moderate': 3}}
        self.assertEqual(self.client.post('/api/guidance/admin/config/', {'values': bad}, format='json').status_code, 400)
        incomplete = {'shortlist': DEFAULTS['shortlist']}
        self.assertEqual(self.client.post('/api/guidance/admin/config/', {'values': incomplete}, format='json').status_code, 400)
        good = {**DEFAULTS, 'academic_tiers': {'strong': 2.5, 'moderate': 5.5}}
        response = self.client.post('/api/guidance/admin/config/', {'values': good, 'activate': True, 'note': 'Panel review'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        active = RecommenderConfig.objects.filter(active_marker='active')
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().values['academic_tiers']['strong'], 2.5)
        entry = AuditLog.objects.get(action='recommender_config_activated')
        self.assertEqual(entry.details['note'], 'Panel review')
        self.assertIn('academic tiers strong:', entry.details['changes'])
        self.assertNotIn('shortlist', entry.details['changes'])
        self.assertEqual(response.data['versions'][0]['created_by'], self.admin.get_full_name() or self.admin.username)

    def test_recommender_status_reports_live_matcher_totals(self):
        student = self.make_student()
        self.consent(student)
        data = self.client.get('/api/guidance/admin/recommender/').data
        self.assertEqual(data['method'], 'ml_recommendation')
        self.assertEqual(data['totals']['assessment_consents'], 1)
        self.assertNotIn(student.user.get_full_name(), repr(data))
        self.assertNotIn('jobs', data)
        self.assertNotIn('alumni_models_ready', data)
        self.assertNotIn('training_snapshots', data['totals'])
        self.assertEqual(self.client.post('/api/guidance/admin/recommender/training/').status_code, 404)
