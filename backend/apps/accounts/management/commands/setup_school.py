from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.console import content_editors_group
from apps.accounts.models import User
from apps.accounts.passwords import check_new_password
from apps.chatbot.seeds import seed_faqs
from apps.cms import defaults as cms_defaults
from apps.cms.models import SiteContent
from apps.guidance.catalog import activate_instrument
from apps.guidance.instrument_seed import CODE, DAMPOL_VERSION, seed_dampol_instrument
from apps.guidance.models import InterestInstrument
from apps.guidance.selectors import active_instrument
from apps.ml.intent import train_intent
from apps.ml.seed import seed_college_programs, seed_program_families
from apps.school.curriculum import carry_forward
from apps.school.models import SchoolYear, Term
from apps.school.offerings import (
    seed_academic_reference,
    seed_matching_exclusions,
    seed_programs,
    seed_strand_groups,
    sync_subject_catalog,
)
from apps.school.term_plan import seed_year_plan

# Local development only. With DEBUG off the first admin needs its own strong --password.
DEV_PASSWORD = 'changeme123'


class Command(BaseCommand):
    help = 'Create the first admin, current school year, programs, and default CMS copy.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEV_PASSWORD, help='Password for the first admin account.')

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        year, _ = SchoolYear.objects.get_or_create(label='2025-2026', defaults={'is_current': True})
        if not year.is_current:
            year.is_current = True
            year.save(update_fields=['is_current'])

        for number in (1, 2, 3):
            Term.objects.get_or_create(
                school_year=year,
                number=number,
                defaults={
                    'label': f'Term {number}',
                    'status': Term.Status.ACTIVE if number == 1 else Term.Status.UPCOMING,
                    'is_current': number == 1,
                },
            )

        seed_programs()
        sync_subject_catalog()
        seed_academic_reference()
        seed_matching_exclusions()
        seed_strand_groups()
        seed_college_programs()
        seed_program_families()
        carry_forward(year)
        seed_year_plan(year)

        admin, created = User.objects.get_or_create(
            email='admin@dampol1nhs.edu.ph',
            defaults={
                'first_name': 'School',
                'last_name': 'Administrator',
                'role': User.Role.ADMIN,
                # Console access for the chatbot FAQs only; maintenance accounts get full access with
                # `manage.py console_access --maintenance`.
                'is_staff': True,
                'is_superuser': False,
                'approval_status': User.ApprovalStatus.APPROVED,
                'account_status': User.AccountStatus.ACTIVE,
            },
        )
        if created:
            if not settings.DEBUG and not settings.TESTING:
                if password == DEV_PASSWORD:
                    raise CommandError('Refused: give the first admin a strong --password. The default is for local use only.')
                try:
                    check_new_password(password, admin)
                except ValidationError as exc:
                    raise CommandError(' '.join(str(item) for item in exc.detail['password'])) from exc
            admin.set_password(password)
            admin.save()
            admin.groups.add(content_editors_group())
            self.stdout.write(self.style.SUCCESS('Created admin@dampol1nhs.edu.ph'))
        else:
            self.stdout.write('Admin account already exists.')

        SiteContent.objects.update_or_create(
            document=SiteContent.Document.LANDING,
            defaults={'payload': cms_defaults.LANDING},
        )
        SiteContent.objects.update_or_create(
            document=SiteContent.Document.ABOUT,
            defaults={'payload': cms_defaults.ABOUT},
        )
        SiteContent.objects.update_or_create(
            document=SiteContent.Document.CONTACT,
            defaults={'payload': cms_defaults.CONTACT},
        )
        SiteContent.objects.update_or_create(
            document=SiteContent.Document.FOOTER,
            defaults={'payload': cms_defaults.FOOTER},
        )

        seed_faqs()
        seed_dampol_instrument(django_apps.get_model)
        instrument = InterestInstrument.objects.get(code=CODE, version=DAMPOL_VERSION)
        current = active_instrument()
        if current is None or current.pk != instrument.pk:
            activate_instrument(instrument, user=admin, license_confirmed=True)
            self.stdout.write(self.style.SUCCESS(f'Activated {instrument}'))

        try:
            train_intent()
        except ValueError as exc:
            self.stdout.write(self.style.WARNING(f'Chatbot intent model not trained: {exc}'))

        self.stdout.write(self.style.SUCCESS('School foundation data is ready.'))
