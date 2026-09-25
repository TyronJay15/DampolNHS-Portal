from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.chatbot.models import FaqEntry
from apps.cms import defaults as cms_defaults
from apps.cms.models import SiteContent
from apps.school.models import SchoolYear, Term
from apps.school.offerings import seed_programs, sync_subject_catalog

FAQS = [
    (
        'registration',
        'register, sign up, create account, registration',
        'How do I register?',
        'Open Register, complete the student form, and submit. Your account stays pending until an administrator approves it.',
    ),
    (
        'programs',
        'stem, abm, humss, ict, he, cluster, program, strand',
        'What programs are offered?',
        'Grade 12 strands are STEM, ABM, HUMSS, ICT, and HE. Grade 11 cluster programs are ASH, BE, STEMC, HT, and ICTP. Choose one on the Programs page, then click Register Now.',
    ),
    (
        'login',
        'login, sign in, lrn, email, password',
        'How do I log in?',
        'Students sign in with LRN and password. Teachers and administrators sign in with school email and password.',
    ),
    (
        'approval',
        'pending, approval, approved, rejected, waiting',
        'Why is my account pending?',
        'New student accounts wait for administrator review. You cannot sign in until the account is approved.',
    ),
    (
        'grades',
        'grades, report card, approved, released',
        'When can I see my grades?',
        'Students only see grades after the Head Teacher approves them and the adviser shows the report card.',
    ),
    (
        'contact',
        'contact, facebook, deped, phone, email, address',
        'How do I contact the school?',
        'Use the Contact page. Official DepEd and school Facebook links are listed there.',
    ),
]


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

        for topic, keywords, question, answer in FAQS:
            FaqEntry.objects.update_or_create(
                question=question,
                defaults={
                    'topic': topic,
                    'keywords': keywords,
                    'answer': answer,
                },
            )

        self.stdout.write(self.style.SUCCESS('School foundation data is ready.'))
