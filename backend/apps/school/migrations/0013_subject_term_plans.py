"""Subjects run in several terms, and each school year keeps its own term plan.

ProgramSubject.term (one term, or empty for every term) becomes ProgramSubject.terms (a list,
empty for every term). Every existing school year then gets a plan copied from those defaults,
so later default edits never change what an earlier year showed.
"""

import django.db.models.deletion
from django.db import migrations, models

TERM_NUMBERS = [1, 2, 3]


def term_to_terms(apps, schema_editor):
    ProgramSubject = apps.get_model('school', 'ProgramSubject')
    for row in ProgramSubject.objects.exclude(term__isnull=True):
        row.terms = [row.term]
        row.save(update_fields=['terms'])


def terms_to_term(apps, schema_editor):
    ProgramSubject = apps.get_model('school', 'ProgramSubject')
    for row in ProgramSubject.objects.all():
        row.term = row.terms[0] if len(row.terms) == 1 else None
        row.save(update_fields=['term'])


def seed_year_plans(apps, schema_editor):
    ProgramSubject = apps.get_model('school', 'ProgramSubject')
    SchoolYear = apps.get_model('school', 'SchoolYear')
    SubjectTermPlan = apps.get_model('school', 'SubjectTermPlan')
    defaults = list(ProgramSubject.objects.all())
    SubjectTermPlan.objects.bulk_create(
        [
            SubjectTermPlan(
                school_year=year,
                program_id=row.program_id,
                subject_id=row.subject_id,
                terms=sorted(row.terms) or TERM_NUMBERS,
            )
            for year in SchoolYear.objects.all()
            for row in defaults
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0012_subject_matching_excluded'),
    ]

    operations = [
        migrations.AddField(
            model_name='programsubject',
            name='terms',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Default term numbers (1-3) the subject runs in; empty means every term. '
                'Each school year copies this into its own term plan.',
            ),
        ),
        migrations.RunPython(term_to_terms, terms_to_term),
        migrations.RemoveConstraint(
            model_name='programsubject',
            name='program_subject_term_1_to_3',
        ),
        migrations.RemoveField(
            model_name='programsubject',
            name='term',
        ),
        migrations.CreateModel(
            name='SubjectTermPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('terms', models.JSONField(default=list, help_text='Term numbers (1-3) the subject runs in this year.')),
                (
                    'program',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='term_plans',
                        to='school.program',
                    ),
                ),
                (
                    'school_year',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='term_plans',
                        to='school.schoolyear',
                    ),
                ),
                (
                    'subject',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='term_plans',
                        to='school.subject',
                    ),
                ),
            ],
            options={
                'db_table': 'school_subject_term_plans',
                'ordering': ['school_year', 'program', 'subject__name'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('school_year', 'program', 'subject'),
                        name='one_term_plan_per_year_program_subject',
                    )
                ],
            },
        ),
        migrations.RunPython(seed_year_plans, migrations.RunPython.noop),
    ]
