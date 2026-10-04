from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.chatbot.seeds import seed_faqs
from apps.cms import defaults as cms_defaults
from apps.cms.models import SiteContent
from apps.ml.intent import train_intent
from apps.ml.seed import seed_college_programs
from apps.school.curriculum import carry_forward
from apps.school.models import SchoolYear, Term
from apps.school.offerings import (
    seed_academic_reference,
    seed_matching_exclusions,
    seed_programs,
    sync_subject_catalog,
)
from apps.school.term_plan import seed_year_plan

class Command(BaseCommand):
    help = 'Create the first admin, current school year, programs, and default CMS copy.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='changeme123')

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
        seed_college_programs()
        carry_forward(year)
        seed_year_plan(year)

        admin, created = User.objects.get_or_create(
            email='admin@dampol1nhs.edu.ph',
            defaults={
                'first_name': 'School',
                'last_name': 'Administrator',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'approval_status': User.ApprovalStatus.APPROVED,
                'account_status': User.AccountStatus.ACTIVE,
            },
        )
        if created:
            admin.set_password(password)
            admin.save()
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

        try:
            train_intent()
        except ValueError as exc:
            self.stdout.write(self.style.WARNING(f'Chatbot intent model not trained: {exc}'))

        self.stdout.write(self.style.SUCCESS('School foundation data is ready.'))
