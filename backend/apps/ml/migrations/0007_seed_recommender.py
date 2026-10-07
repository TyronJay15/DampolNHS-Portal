from django.db import migrations
from django.utils import timezone

DRAFT_SOURCE = 'Catalog seed drafted with AI assistance. Pending an authoritative source and expert validation.'


def seed(apps, schema_editor):
    from apps.ml.recommender_config import ACTIVE, DEFAULTS
    from apps.ml.seed import seed_program_families

    seed_program_families(apps.get_model)

    config_model = apps.get_model('ml', 'RecommenderConfig')
    if not config_model.objects.exists():
        config_model.objects.create(
            version=1,
            values=DEFAULTS,
            note='Provisional defaults documented in apps/ml/recommender_config.py, awaiting panel approval.',
            is_approved=False,
            activated_at=timezone.now(),
            active_marker=ACTIVE,
        )

    # Version 1 of every existing profile is recorded as an unvalidated draft, so its history starts here.
    college_model = apps.get_model('ml', 'CollegeProgram')
    snapshot_model = apps.get_model('ml', 'ProgramProfileSnapshot')
    for college in college_model.objects.prefetch_related('skills__domain'):
        if snapshot_model.objects.filter(college_program=college).exists():
            continue
        snapshot_model.objects.create(
            college_program=college,
            version=college.profile_version,
            status='draft',
            rows=[
                {
                    'domain': skill.domain.key,
                    'level': str(skill.level),
                    'minimum': str(skill.minimum) if skill.minimum is not None else None,
                    'minimum_kind': skill.minimum_kind,
                    'requirement_source': skill.requirement_source,
                }
                for skill in college.skills.all()
            ],
            source=DRAFT_SOURCE,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('ml', '0006_recommender_catalog_and_models'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
