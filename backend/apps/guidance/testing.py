"""Shared test fixtures for the guidance tests. Synthetic rows here exist only inside the test database."""

from datetime import date
from decimal import Decimal
from itertools import count

from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.guidance import catalog
from apps.guidance.consent import NOTICE_VERSION
from apps.guidance.instrument_seed import CODE, DAMPOL_VERSION
from apps.guidance.models import GuidanceConsent, InterestAssessment, InterestInstrument
from apps.ml.models import CollegeOutcome, CollegeProgram
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, SkillDomain, Subject, Term

ADULT_BIRTHDATE = date(timezone.localdate().year - 19, 1, 1)
PROFILES = {
    'tech': {'tech': 95, 'math': 88, 'language': 82, 'social': 80},
    'science': {'science': 94, 'math': 90, 'language': 80, 'social': 78},
    'business': {'business': 93, 'math': 85, 'language': 84, 'social': 80},
}
INTERESTS = {
    'tech': {'R': 3.0, 'I': 4.6, 'A': 2.4, 'S': 2.2, 'E': 2.8, 'C': 4.4},
    'science': {'R': 2.6, 'I': 4.8, 'A': 2.2, 'S': 4.4, 'E': 2.0, 'C': 3.0},
    'business': {'R': 2.0, 'I': 2.4, 'A': 2.6, 'S': 3.2, 'E': 4.8, 'C': 4.2},
}
_serial = count(1)


class GuidanceFixture:
    """A school year, an ICT section with an adviser, and helpers to build students."""

    def setUp(self):
        super().setUp()
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.shs_program = Program.objects.create(code='ICTP', name='ICT Programming', strand_group='ICT', sort_order=1)
        self.section = Section.objects.create(school_year=self.year, name='A', grade_level='Grade 12', program=self.shs_program)
        self.adviser = self.make_user(User.Role.TEACHER, 'adviser')
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.adviser,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )
        self.admin = self.make_user(User.Role.ADMIN, 'admin')
        self.instrument = InterestInstrument.objects.get(code=CODE, version=DAMPOL_VERSION)
        catalog.activate_instrument(self.instrument, user=self.admin, license_confirmed=True)
        self.subjects = {}

    def make_user(self, role, name):
        number = next(_serial)
        # No usable password: tests sign in with force_authenticate, and skipping the hash keeps them fast.
        return User.objects.create_user(
            email=f'{name}{number}@example.com',
            password=None,
            first_name=name.title(),
            last_name=f'User{number}',
            role=role,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def subject_for(self, domain):
        if domain not in self.subjects:
            self.subjects[domain] = Subject.objects.create(
                code=f'subj-{domain}',
                name=domain.title(),
                skill_domain=SkillDomain.objects.get(key=domain),
            )
        return self.subjects[domain]

    def make_student(self, profile='tech', *, status=Grade.Status.RELEASED, section=None, adult=True, jitter=0):
        user = self.make_user(User.Role.STUDENT, 'student')
        student = StudentProfile.objects.create(
            user=user,
            lrn=f'1360{next(_serial):08d}',
            birthdate=ADULT_BIRTHDATE if adult else None,
        )
        StudentSection.objects.create(student=student, section=section or self.section, school_year=self.year)
        for domain, score in PROFILES[profile].items():
            Grade.objects.create(
                student=student,
                subject=self.subject_for(domain),
                term=self.term,
                school_year=self.year,
                score=Decimal(score - jitter),
                status=status,
            )
        return student

    def consent(self, student, *kinds):
        for kind in kinds or (GuidanceConsent.Kind.ASSESSMENT,):
            GuidanceConsent.objects.create(
                student=student,
                kind=kind,
                party=GuidanceConsent.Party.STUDENT,
                notice_version=NOTICE_VERSION,
                active_marker=f'{student.pk}:{kind}',
            )

    def complete_assessment(self, student, profile='tech'):
        return InterestAssessment.objects.create(
            student=student,
            instrument=self.instrument,
            status=InterestAssessment.Status.COMPLETED,
            scores=INTERESTS[profile],
            completed_at=timezone.now(),
        )

    def labeled_student(self, profile, program_code, *, synthetic=False, jitter=0):
        """A graduate with consent, an assessment and a validated outcome: one training record."""
        student = self.make_student(profile, jitter=jitter)
        self.consent(student, GuidanceConsent.Kind.ASSESSMENT, GuidanceConsent.Kind.TRAINING)
        self.complete_assessment(student, profile)
        CollegeOutcome.objects.create(
            student=student,
            college_program=CollegeProgram.objects.get(code=program_code),
            school_year=self.year,
            status=CollegeOutcome.Status.VALIDATED,
            recorded_by=self.adviser,
            validated_by=self.admin,
            validated_at=timezone.now(),
            is_synthetic=synthetic,
        )
        return student

    def grant(self, user, *codenames):
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(content_type__app_label='ml', codename=codename))
        return User.objects.get(pk=user.pk)
