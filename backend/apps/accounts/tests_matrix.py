"""Every API route, called as every role (security plan sections 21, 27 and 59).

Access matrix: each route and method is called signed out and as a student, teacher, head teacher and admin, and
each answer is classed as "sign-in" (401), "refused" (403) or "allowed" (the role check let it through; the answer
may still be 400 or 404 for the sample request). The classes must match apps/accounts/security_matrix.json, which a
person reviews. Classes rather than exact codes keep the test stable: record ids differ between test runs. A new route without an entry
fails the test, so nobody can add an endpoint without stating who may use it. After a deliberate change, rewrite
the file with  SECURITY_MATRIX_RECORD=1 python manage.py test apps.accounts.tests_matrix  and review the diff.

Hostile input: every route gets malformed ids, wrong types, huge values and broken JSON. Nothing may answer with a
server error, and no answer may contain internals (tracebacks, file paths, SQL).
"""

import json
import os
import re
from pathlib import Path

from django.core.cache import cache
from django.db import transaction
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear, Section, Subject, Term

MATRIX_FILE = Path(__file__).with_name('security_matrix.json')
ROLES = ('anonymous', 'student', 'teacher', 'head_teacher', 'admin')
METHODS = ('get', 'post', 'put', 'patch', 'delete')
# Routes that end something for everyone in the run, called separately by their own tests.
SKIPPED = ('/purge/',)
SAMPLE_SLUGS = {'code': 'sample', 'action': 'verify', 'role': 'recommender_family'}
LEAK_MARKERS = ('Traceback', 'File "', 'C:\\\\', '/home/', 'django.db', 'OperationalError', 'SELECT ', 'mysql')
LONG = 'A' * 20000
HOSTILE_BODIES = [
    {'id': 'abc', 'ids': 'x', 'term': 'abc', 'student': 'abc', 'assignment': 'abc', 'section': 'abc', 'reason': LONG},
    {'ids': [None, {}, []], 'term': None, 'score': 'NaN', 'url': 'javascript:alert(1)', 'name': "'; DROP TABLE x;--"},
    {'ids': [1] * 5000, 'x': {'y': [1] * 50}, 'student': 10**30, 'email': '<script>alert(1)</script>@x.com', 'label': '\x00'},
]
HOSTILE_QUERIES = [
    '?student=abc&term=abc&school_year=abc&assignment=abc&section=abc&search=%27%22%3C&ordering=-password&page=-1',
    '?student=999999999999999999999&term=-1&school_year=1e9&assignment=NaN&kind=../../etc&program=%27',
]


def concrete(route):
    """A callable address for a route pattern: ids become 1, slugs become sample values, router regexes are undone."""
    # Router regexes first: their "(?P<pk>...)" would otherwise be half-replaced by the <name> rule below.
    route = re.sub(r'\(\?P<[a-z_]+>\[\^/\.\]\+\)', '1', route)
    route = re.sub(r'<slug:([a-z_]+)>', lambda match: SAMPLE_SLUGS.get(match.group(1), 'sample'), route)
    route = re.sub(r'<(?:int:)?[a-z_]+>', '1', route)
    return route.replace('^', '').replace('$', '')


def access_class(status):
    return {401: 'sign-in', 403: 'refused'}.get(status, 'allowed')


def routes():
    """(method, concrete url, view) for every API route."""
    found = []

    def walk(patterns, prefix=''):
        for item in patterns:
            if isinstance(item, URLResolver):
                walk(item.url_patterns, prefix + str(item.pattern))
            elif isinstance(item, URLPattern):
                found.append((prefix + str(item.pattern), item.callback))

    walk(get_resolver().url_patterns)
    result = []
    for route, callback in found:
        if not route.startswith('api/') or any(part in route for part in SKIPPED):
            continue
        url = '/' + concrete(route)
        if '(?P' in url or '<' in url or '\\' in url:
            continue  # the router's ".json" format-suffix variants
        view = getattr(callback, 'view_class', None) or getattr(callback, 'cls', None)
        if view is None:
            continue
        actions = getattr(callback, 'actions', None)
        methods = [m for m in actions if m in METHODS] if actions else [m for m in METHODS if hasattr(view, m)]
        result.extend((method.upper(), url, view) for method in methods)
    return sorted(set((method, url) for method, url, _view in result))


class MatrixFixture(TestCase):
    def setUp(self):
        cache.clear()
        year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        Term.objects.create(school_year=year, number=1, label='Term 1', status='active', is_current=True)
        programs = make_programs()
        self.users = {
            role: User.objects.create_user(
                email=f'{role}@x.com', password='Strongpass1!', role=role,
                approval_status=User.ApprovalStatus.APPROVED, account_status=User.AccountStatus.ACTIVE,
            )
            for role in ROLES[1:]
        }
        profile = StudentProfile.objects.create(user=self.users['student'], lrn='136000000001')
        section = Section.objects.create(school_year=year, name='STEMC-A', grade_level='Grade 11', program=programs['STEMC'])
        StudentSection.objects.create(student=profile, section=section, school_year=year)
        subject = Subject.objects.create(code='gm', name='General Math')
        TeacherAssignment.objects.create(
            teacher=self.users['teacher'], assignment_type='subject_teacher', status='active',
            school_year=year, section=section, subject=subject,
        )
        pending = User.objects.create_user(
            email='p@x.com', password='Strongpass1!', role='student', approval_status='pending', account_status='active'
        )
        Registration.objects.create(
            user=pending, school_year=year, program=programs['STEMC'], grade_level_enrollment='Grade 11', status='pending'
        )

    def client_as(self, role):
        client = APIClient(raise_request_exception=False)
        if role != 'anonymous':
            client.force_authenticate(user=self.users[role])
        return client

    def call(self, role, method, url, body=None, raw=None):
        """One request inside a rolled-back transaction, so no call changes what the next one sees."""
        with transaction.atomic():
            client = self.client_as(role)
            if raw is not None:
                response = getattr(client, method.lower())(url, data=raw, content_type='application/json')
            elif method == 'GET':
                response = client.get(url)
            else:
                response = getattr(client, method.lower())(url, body if body is not None else {}, format='json')
            transaction.set_rollback(True)
        return response


class AccessMatrixTests(MatrixFixture):
    def test_every_route_answers_each_role_as_reviewed(self):
        actual = {}
        for method, url in routes():
            actual[f'{method} {url}'] = {role: access_class(self.call(role, method, url).status_code) for role in ROLES}
        if os.environ.get('SECURITY_MATRIX_RECORD'):
            MATRIX_FILE.write_text(json.dumps(actual, indent=1, sort_keys=True) + '\n', encoding='utf-8')
            self.skipTest(f'Recorded {len(actual)} routes to {MATRIX_FILE.name}; review the diff before committing.')
        expected = json.loads(MATRIX_FILE.read_text(encoding='utf-8'))
        unreviewed = sorted(set(actual) - set(expected))
        self.assertEqual(unreviewed, [], 'New routes need an entry in security_matrix.json (see the module docstring).')
        changed = {key: {'expected': expected[key], 'actual': actual[key]} for key in actual if actual[key] != expected[key]}
        self.assertEqual(changed, {}, 'Access changed. If deliberate, record the matrix again and review it.')

    def test_signed_out_visitors_reach_only_the_public_routes(self):
        public = {
            'GET /api/health/', 'GET /api/health/ready/', 'GET /api/programs/', 'GET /api/programs/1/', 'GET /api/announcements/',
            'GET /api/announcements/1/',
            'GET /api/cms/content/', 'POST /api/chatbot/', 'GET /api/auth/csrf/', 'POST /api/auth/login/',
            'POST /api/auth/refresh/', 'POST /api/auth/logout/', 'POST /api/auth/activate/', 'POST /api/register/',
            'POST /api/auth/forgot-password/otp/', 'POST /api/auth/forgot-password/verify/', 'POST /api/auth/forgot-password/',
        }
        expected = json.loads(MATRIX_FILE.read_text(encoding='utf-8'))
        reachable = {key for key, row in expected.items() if row['anonymous'] == 'allowed'}
        self.assertLessEqual(reachable, public, reachable - public)


class HostileInputTests(MatrixFixture):
    def test_no_route_crashes_or_leaks_internals_on_hostile_input(self):
        crashes, leaks = [], []
        for method, url in routes():
            attempts = [(url + query, None, None) for query in HOSTILE_QUERIES] if method == 'GET' else (
                [(url, body, None) for body in HOSTILE_BODIES] + [(url, None, 'not json {{{')]
            )
            for role in ('anonymous', 'student', 'head_teacher', 'admin'):
                for target, body, raw in attempts:
                    response = self.call(role, method, target, body, raw)
                    text = response.content[:3000].decode('utf-8', 'ignore') if response.content else ''
                    if response.status_code >= 500:
                        crashes.append(f'{method} {target} as {role}: {response.status_code}')
                    if any(marker in text for marker in LEAK_MARKERS):
                        leaks.append(f'{method} {target} as {role}')
        self.assertEqual(crashes, [])
        self.assertEqual(leaks, [])
