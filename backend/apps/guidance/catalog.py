"""Admin maintenance of the college catalog, program profiles, the family interest map and instruments.

Rules enforced here (the database cannot enforce them on existing rows):
  - a program can only be switched on with an authoritative source, a verification date and a profile
    validated by experts; programs that were active before this module stay active, shown as drafts;
  - a program profile changes only by applying expert ratings (median of at least MIN_RATERS raters),
    and every change writes a ProgramProfileSnapshot;
  - an official requirement always carries its source.
Every change is audited.
"""

import csv
import io
import re
import statistics
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit import services as audit
from apps.guidance.models import InterestInstrument, InterestQuestion
from apps.ml.features import RIASEC_ORDER, distance, to_model_space
from apps.ml.models import (
    CollegeProgram,
    CollegeProgramSkill,
    FamilyInterestMap,
    ProgramFamily,
    ProgramProfileSnapshot,
    ProgramSkillRating,
)
from apps.notifications.services import active_users, notify
from apps.school.models import Program, SkillDomain

# At least three independent expert ratings per skill area before a profile can be validated, so no single
# opinion defines a program (plan: expert validation, median aggregation).
MIN_RATERS = 3
# Ratings that differ by this many mapped points or more block Apply until the experts revise them.
DISAGREEMENT_POINTS = Decimal('12')
# Teachers rate relative importance, not a typical-grade number. These points become the profile levels
# the matcher compares; they are not a claim that every graduate scores 95.
IMPORTANCE = {
    'much_less': Decimal('60.00'),
    'less': Decimal('70.00'),
    'typical': Decimal('75.00'),
    'more': Decimal('85.00'),
    'much_more': Decimal('95.00'),
}
IMPORTANCE_LABELS = {
    'much_less': 'Much less important than usual',
    'less': 'Less important than usual',
    'typical': 'About as important as usual',
    'more': 'More important than usual',
    'much_more': 'Much more important than usual',
}
_LEVEL_TO_IMPORTANCE = {value: key for key, value in IMPORTANCE.items()}
CLONE_DISTANCE = 1e-6
CODE_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{1,31}$')
IMPORT_COLUMNS = (
    'code',
    'name',
    'abbreviation',
    'family',
    'description',
    'career_overview',
    'source',
    'source_url',
    'verified_on',
)
REQUIRED_IMPORT_COLUMNS = ('code', 'name', 'family')
TEXT_LIMITS = {'name': 160, 'abbreviation': 24, 'source': 255, 'source_url': 200, 'description': 4000, 'career_overview': 4000}


def _text(data, field, *, required=False, limit=None):
    value = str(data.get(field) or '').strip()
    limit = limit or TEXT_LIMITS.get(field)
    if required and not value:
        raise ValidationError({field: 'This field is required.'})
    if limit and len(value) > limit:
        raise ValidationError({field: f'Use at most {limit} characters.'})
    return value


def _code(value, field='code'):
    code = str(value or '').strip().lower()
    if not CODE_PATTERN.match(code):
        raise ValidationError({field: 'Use 2 to 32 lowercase letters, digits or hyphens, starting with a letter or digit.'})
    return code


def _url(value):
    url = str(value or '').strip()
    if url and not url.startswith(('https://', 'http://')):
        raise ValidationError({'source_url': 'Enter a full web address starting with https://.'})
    if len(url) > TEXT_LIMITS['source_url']:
        raise ValidationError({'source_url': 'The address is too long.'})
    return url


def _date(value, field='verified_on'):
    if value in (None, ''):
        return None
    if isinstance(value, date):
        return value
    try:
        parsed = date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValidationError({field: 'Use the date format YYYY-MM-DD.'}) from exc
    if parsed > timezone.localdate():
        raise ValidationError({field: 'The verification date cannot be in the future.'})
    return parsed


def _grade(value, field):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({field: 'Enter a grade from 0 to 100.'}) from exc
    if not number.is_finite() or not Decimal('0') <= number <= Decimal('100'):
        raise ValidationError({field: 'Enter a grade from 0 to 100.'})
    return number.quantize(Decimal('0.01'))


def _family(code):
    family = ProgramFamily.objects.filter(code=code).first()
    if family is None:
        raise ValidationError({'family': 'Choose an existing program family.'})
    return family


# ---- Families ---------------------------------------------------------------------------------------


def save_family(data, *, user, family=None):
    name = _text(data, 'name', required=True, limit=120)
    is_active = bool(data.get('is_active', True)) if family else True
    with transaction.atomic():
        if family is None:
            code = _code(data.get('code'))
            if ProgramFamily.objects.filter(code=code).exists():
                raise ValidationError({'code': 'A family with this code already exists.'})
            order = (ProgramFamily.objects.order_by('-sort_order').values_list('sort_order', flat=True).first() or 0) + 1
            family = ProgramFamily.objects.create(code=code, name=name, sort_order=order)
        else:
            if not is_active and family.programs.filter(is_active=True).exists():
                raise ValidationError({'is_active': 'Move or switch off its active programs before retiring this family.'})
            family.name = name
            family.is_active = is_active
            family.save(update_fields=['name', 'is_active'])
    audit.record(
        user=user,
        action='program_family_saved',
        summary=f'Program family saved: {family.name}',
        target_type='ProgramFamily',
        target_id=family.pk,
    )
    return family


def save_interest_map(mapping, *, user):
    """mapping: family code -> list of RIASEC letters. Replaces the map for the families given."""
    if not isinstance(mapping, dict) or not mapping:
        raise ValidationError({'detail': 'Send the interest types for at least one family.'})
    families = {row.code: row for row in ProgramFamily.objects.filter(code__in=list(mapping))}
    clean = {}
    for code, letters in mapping.items():
        if code not in families:
            raise ValidationError({'detail': f'Unknown family {code}.'})
        if not isinstance(letters, list) or not 1 <= len(set(letters)) <= 3 or set(letters) - set(RIASEC_ORDER):
            raise ValidationError({'detail': f'Give {families[code].name} one to three interest types (R, I, A, S, E, C).'})
        clean[code] = sorted(set(letters), key=RIASEC_ORDER.index)
    with transaction.atomic():
        for code, letters in clean.items():
            FamilyInterestMap.objects.filter(family=families[code]).delete()
            FamilyInterestMap.objects.bulk_create([FamilyInterestMap(family=families[code], riasec=letter) for letter in letters])
    audit.record(
        user=user,
        action='interest_map_saved',
        summary=f'Family interest map saved for {len(clean)} famil{"y" if len(clean) == 1 else "ies"}',
        target_type='FamilyInterestMap',
        details={'map': clean},
    )
    return clean


# ---- Programs ---------------------------------------------------------------------------------------

PROGRAM_TEXT_FIELDS = ('name', 'abbreviation', 'description', 'career_overview', 'source')


def create_program(data, *, user):
    code = _code(data.get('code'))
    if CollegeProgram.objects.filter(code=code).exists():
        raise ValidationError({'code': 'A program with this code already exists.'})
    values = {field: _text(data, field, required=field == 'name') for field in PROGRAM_TEXT_FIELDS}
    order = (CollegeProgram.objects.order_by('-sort_order').values_list('sort_order', flat=True).first() or 0) + 1
    program = CollegeProgram.objects.create(
        code=code,
        family=_family(data.get('family')),
        source_url=_url(data.get('source_url')),
        is_active=False,
        sort_order=order,
        **values,
    )
    audit.record(
        user=user,
        action='college_program_added',
        summary=f'College program added (not yet active): {program.name}',
        target_type='CollegeProgram',
        target_id=program.pk,
    )
    return program


def update_program(program, data, *, user):
    changed = []
    for field in PROGRAM_TEXT_FIELDS:
        if field in data:
            value = _text(data, field, required=field == 'name')
            if getattr(program, field) != value:
                setattr(program, field, value)
                changed.append(field)
    if 'source_url' in data:
        url = _url(data.get('source_url'))
        if url != program.source_url:
            program.source_url = url
            changed.append('source_url')
    if 'family' in data:
        family = _family(data.get('family'))
        if family.pk != program.family_id:
            program.family = family
            changed.append('family')
    if 'is_active' in data:
        active = data.get('is_active') is True
        if active and not program.is_active:
            _require_activation_ready(program)
        if active != program.is_active:
            program.is_active = active
            changed.append('is_active')
    pathways = _pathways(data['shs_programs']) if 'shs_programs' in data else None
    if pathways is not None and {row.pk for row in pathways} != set(program.shs_programs.values_list('pk', flat=True)):
        program.shs_programs.set(pathways)
        changed.append('shs_programs')
    if not changed:
        return program
    fields = [field for field in changed if field != 'shs_programs']
    if fields:
        program.save(update_fields=fields)
    audit.record(
        user=user,
        action='college_program_updated',
        summary=f'College program updated: {program.name}',
        target_type='CollegeProgram',
        target_id=program.pk,
        details={'fields': changed},
    )
    return program


def _pathways(codes):
    """The SHS programs that usually lead to a college program (strand context only, never a restriction)."""
    if not isinstance(codes, list) or any(not isinstance(code, str) for code in codes):
        raise ValidationError({'shs_programs': 'Send a list of SHS program codes.'})
    wanted = set(codes)
    rows = list(Program.objects.filter(code__in=wanted))
    if len(rows) != len(wanted):
        raise ValidationError({'shs_programs': 'One or more SHS programs do not exist.'})
    return rows


def _require_activation_ready(program):
    missing = []
    if program.verification_status != CollegeProgram.Verification.VERIFIED or not program.source or not program.verified_on:
        missing.append('a verified authoritative source with its date')
    if program.profile_status != CollegeProgram.ProfileStatus.VALIDATED:
        missing.append('a profile validated by experts')
    if program.family_id is None or not program.family.is_active:
        missing.append('an active program family')
    if missing:
        raise ValidationError({'is_active': f'Before switching this program on, it needs {" and ".join(missing)}.'})


def verify_program(program, data, *, user):
    source = _text(data, 'source', required=True)
    verified_on = _date(data.get('verified_on'))
    if verified_on is None:
        raise ValidationError({'verified_on': 'Enter the date the source was checked.'})
    program.source = source
    program.source_url = _url(data.get('source_url'))
    program.verified_on = verified_on
    program.verified_by = user
    program.verification_status = CollegeProgram.Verification.VERIFIED
    program.save(update_fields=['source', 'source_url', 'verified_on', 'verified_by', 'verification_status'])
    audit.record(
        user=user,
        action='college_program_verified',
        summary=f'College program verified: {program.name}',
        target_type='CollegeProgram',
        target_id=program.pk,
        details={'source': source, 'verified_on': verified_on.isoformat()},
    )
    return program


def set_official_requirement(program, data, *, user):
    """Mark a profile benchmark as an official requirement with its source, or turn it back into a benchmark."""
    skill = program.skills.filter(domain__key=str(data.get('domain') or '')).select_related('domain').first()
    if skill is None:
        raise ValidationError({'domain': 'Choose a skill area that is part of this program profile.'})
    if data.get('official') is True:
        skill.minimum = _grade(data.get('minimum'), 'minimum')
        skill.minimum_kind = CollegeProgramSkill.MinimumKind.OFFICIAL
        skill.requirement_source = _text(data, 'source', required=True)
    else:
        skill.minimum_kind = CollegeProgramSkill.MinimumKind.BENCHMARK
        skill.requirement_source = ''
    skill.save(update_fields=['minimum', 'minimum_kind', 'requirement_source'])
    _snapshot(program, user=user, note=f'{skill.domain.label}: requirement changed', validators=[])
    audit.record(
        user=user,
        action='college_program_updated',
        summary=f'Requirement changed for {program.name}: {skill.domain.label}',
        target_type='CollegeProgram',
        target_id=program.pk,
        details={'domain': skill.domain.key, 'kind': skill.minimum_kind, 'source': skill.requirement_source},
    )
    return skill


# ---- Profiles from expert ratings ---------------------------------------------------------------------


def rating_round(program):
    return program.profile_version + 1


def importance_of(level):
    return _LEVEL_TO_IMPORTANCE.get(Decimal(str(level)).quantize(Decimal('0.01')), '')


def _active_domains():
    return list(SkillDomain.objects.filter(is_active=True).order_by('sort_order', 'key'))


def rating_summary(program):
    """Per skill area: the ratings of the current round, their median, and the gates that block Apply."""
    round_number = rating_round(program)
    ratings = list(
        ProgramSkillRating.objects.filter(college_program=program, round=round_number)
        .select_related('domain', 'rater')
        .order_by('domain__sort_order', 'rater_id')
    )
    domains = _active_domains()
    areas = {
        domain.key: {
            'domain': domain.key,
            'label': domain.label,
            'levels': [],
            'benchmarks': [],
            'raters': set(),
            'importance': [],
        }
        for domain in domains
    }
    for row in ratings:
        area = areas.get(row.domain.key)
        if area is None:
            continue
        area['levels'].append(row.level)
        area['raters'].add(row.rater_id)
        area['importance'].append(importance_of(row.level))
        if row.benchmark is not None:
            area['benchmarks'].append(row.benchmark)
    summary = []
    for domain in domains:
        area = areas[domain.key]
        levels = area['levels']
        disagree = bool(levels) and max(levels) - min(levels) >= DISAGREEMENT_POINTS
        summary.append(
            {
                'domain': area['domain'],
                'label': area['label'],
                'raters': len(area['raters']),
                'levels': [str(value) for value in levels],
                'importance': area['importance'],
                'median': str(statistics.median(levels)) if levels else None,
                'median_importance': importance_of(statistics.median(levels)) if levels else '',
                'benchmark_median': str(statistics.median(area['benchmarks'])) if len(area['benchmarks']) >= MIN_RATERS else None,
                'disagree': disagree,
            }
        )
    enough = bool(summary) and all(area['raters'] >= MIN_RATERS for area in summary)
    medians = {area['domain']: Decimal(area['median']) for area in summary if area['median']}
    blockers = []
    missing = [area['label'] for area in summary if area['raters'] < MIN_RATERS]
    if missing:
        blockers.append(
            {
                'code': 'raters',
                'detail': f'Every skill area needs ratings from at least {MIN_RATERS} experts. Still needed: {", ".join(missing)}.',
            }
        )
    disagreeing = [area['label'] for area in summary if area['disagree']]
    if disagreeing:
        blockers.append(
            {
                'code': 'disagree',
                'detail': f'Experts still disagree by {DISAGREEMENT_POINTS} points or more in {", ".join(disagreeing)}. They must revise before this profile can be applied.',
            }
        )
    if enough and medians and max(medians.values()) == min(medians.values()):
        blockers.append(
            {
                'code': 'flat',
                'detail': 'This profile rates every skill area the same. Mark which areas matter more or less for this program.',
            }
        )
    clone = _clone_of(program, medians) if enough and medians else None
    if clone:
        blockers.append(
            {
                'code': 'clone',
                'detail': f'This relative-importance pattern matches {clone}. Rate this program on its own strengths.',
            }
        )
    return {
        'round': round_number,
        'min_raters': MIN_RATERS,
        'disagreement_points': str(DISAGREEMENT_POINTS),
        'importance': [{'key': key, 'label': label, 'level': str(IMPORTANCE[key])} for key, label in IMPORTANCE_LABELS.items()],
        'areas': summary,
        'ready': enough and not blockers,
        'blockers': blockers,
        'raters': sorted({row.rater.get_full_name() or row.rater.email for row in ratings}),
    }


def _clone_of(program, medians):
    """Name of another validated program with the same relative-importance vector, or None."""
    keys = tuple(medians)
    proposed = to_model_space(tuple(medians[key] for key in keys), tuple(True for _key in keys))
    others = (
        CollegeProgram.objects.filter(profile_status=CollegeProgram.ProfileStatus.VALIDATED)
        .exclude(pk=program.pk)
        .prefetch_related('skills__domain')
    )
    for other in others:
        levels = {skill.domain.key: skill.level for skill in other.skills.all() if skill.domain.key in medians}
        if len(levels) != len(medians):
            continue
        vector = to_model_space(tuple(levels.get(key) for key in keys), tuple(key in levels for key in keys))
        if distance(proposed, vector) <= CLONE_DISTANCE:
            return other.name
    return None


def apply_ratings(program, *, user, source, note=''):
    """Replace the profile with the median expert ratings of the current round and record the new version."""
    summary = rating_summary(program)
    if summary['blockers']:
        raise ValidationError({'detail': summary['blockers'][0]['detail']})
    if not summary['ready']:
        raise ValidationError({'detail': f'Every skill area needs ratings from at least {MIN_RATERS} experts first.'})
    source = str(source or '').strip()[:255]
    if not source:
        raise ValidationError({'source': 'Name the official program information the experts worked from.'})
    domains = {row.key: row for row in SkillDomain.objects.filter(key__in=[area['domain'] for area in summary['areas']])}
    official = {skill.domain_id: skill for skill in program.skills.filter(minimum_kind=CollegeProgramSkill.MinimumKind.OFFICIAL)}
    with transaction.atomic():
        program = CollegeProgram.objects.select_for_update().get(pk=program.pk)
        if rating_round(program) != summary['round']:
            raise ValidationError({'detail': 'This profile was updated at the same moment. Reload and try again.'})
        program.skills.exclude(domain_id__in=official).delete()
        for area in summary['areas']:
            domain = domains[area['domain']]
            if domain.pk in official:
                skill = official[domain.pk]
                skill.level = Decimal(area['median'])
                skill.save(update_fields=['level'])
                continue
            CollegeProgramSkill.objects.create(
                college_program=program,
                domain=domain,
                level=Decimal(area['median']),
                minimum=Decimal(area['benchmark_median']) if area['benchmark_median'] else None,
            )
        program.profile_version = summary['round']
        program.profile_status = CollegeProgram.ProfileStatus.VALIDATED
        program.save(update_fields=['profile_version', 'profile_status'])
        validators = sorted(
            set(ProgramSkillRating.objects.filter(college_program=program, round=summary['round']).values_list('rater_id', flat=True))
        )
        _snapshot(program, user=user, note=note or 'Median of expert ratings applied', validators=validators, source=source)
    audit.record(
        user=user,
        action='program_profile_applied',
        summary=f'Program profile v{program.profile_version} validated: {program.name}',
        target_type='CollegeProgram',
        target_id=program.pk,
        details={'raters': summary['raters'], 'source': source},
    )
    return program


def _snapshot(program, *, user, note, validators, source=''):
    program.refresh_from_db(fields=['profile_version', 'profile_status', 'source'])
    rows = [
        {
            'domain': skill.domain.key,
            'level': str(skill.level),
            'minimum': str(skill.minimum) if skill.minimum is not None else None,
            'minimum_kind': skill.minimum_kind,
            'requirement_source': skill.requirement_source,
        }
        for skill in program.skills.select_related('domain').order_by('domain__sort_order')
    ]
    ProgramProfileSnapshot.objects.update_or_create(
        college_program=program,
        version=program.profile_version,
        defaults={
            'status': program.profile_status,
            'rows': rows,
            'source': source or program.source,
            'validators': validators,
            'note': note[:255],
            'created_by': user,
        },
    )


def _rating_fingerprint(rows):
    return tuple(sorted((row['domain'], str(row['level']), row.get('benchmark')) for row in rows))


def _stored_fingerprint(program, rater, round_number):
    rows = ProgramSkillRating.objects.filter(college_program=program, rater=rater, round=round_number).select_related('domain')
    return tuple(
        sorted(
            (row.domain.key, str(row.level), str(row.benchmark) if row.benchmark is not None else None)
            for row in rows
        )
    )


def save_ratings(program, rater, ratings):
    """Store one expert's ratings for the current round (called when the Admin approves the rater's request)."""
    round_number = rating_round(program)
    if _stored_fingerprint(program, rater, round_number) == _rating_fingerprint(ratings):
        raise ValidationError(
            {'detail': 'These ratings were already recorded. Change the relative importance if experts still disagree.'}
        )
    domains = {row.key: row for row in SkillDomain.objects.filter(is_active=True)}
    with transaction.atomic():
        for row in ratings:
            ProgramSkillRating.objects.update_or_create(
                college_program=program,
                domain=domains[row['domain']],
                rater=rater,
                round=round_number,
                defaults={
                    'level': Decimal(row['level']),
                    'benchmark': Decimal(row['benchmark']) if row.get('benchmark') is not None else None,
                },
            )
    summary = rating_summary(program)
    if any(blocker['code'] == 'disagree' for blocker in summary['blockers']):
        _notify_disagreement(program, summary)
    return round_number


def _notify_disagreement(program, summary):
    names = ', '.join(area['label'] for area in summary['areas'] if area['disagree'])
    body = (
        f'Expert ratings for {program.name} still disagree by {DISAGREEMENT_POINTS} points or more in {names}. '
        'Apply is blocked until the experts revise those skill areas. Submitting the same ratings again is refused.'
    )
    recipients = list(active_users(User.Role.ADMIN))
    rater_ids = ProgramSkillRating.objects.filter(college_program=program, round=summary['round']).values_list(
        'rater_id', flat=True
    )
    recipients.extend(User.objects.filter(pk__in=rater_ids))
    notify(
        recipients,
        f'Program ratings need a review · {program.name}',
        body,
        action_path=f'/admin/guidance/programs/{program.code}',
        category='guidance',
    )


def _importance_level(row):
    key = str(row.get('importance') or '').strip()
    if key in IMPORTANCE:
        return key, IMPORTANCE[key]
    if row.get('level') in (None, ''):
        raise ValidationError({'detail': 'Choose how important each skill area is compared with a typical Grade 12 graduate.'})
    level = _grade(row.get('level'), 'level')
    if level not in _LEVEL_TO_IMPORTANCE:
        raise ValidationError({'detail': 'Choose how important each skill area is compared with a typical Grade 12 graduate.'})
    return _LEVEL_TO_IMPORTANCE[level], level


def clean_ratings(ratings):
    """Validate a rater's submission: every active skill area, as relative importance."""
    domains = list(_active_domains())
    keys = {domain.key for domain in domains}
    if not isinstance(ratings, list) or not ratings:
        raise ValidationError({'detail': 'Rate every skill area for this program.'})
    clean = []
    seen = set()
    for row in ratings:
        if not isinstance(row, dict) or row.get('domain') not in keys or row['domain'] in seen:
            raise ValidationError({'detail': 'Each rating needs a different, active skill area.'})
        seen.add(row['domain'])
        _key, level = _importance_level(row)
        benchmark = row.get('benchmark')
        benchmark = _grade(benchmark, 'benchmark') if benchmark not in (None, '') else None
        if benchmark is not None and benchmark > level:
            raise ValidationError({'detail': 'A benchmark cannot be higher than the mapped importance for that skill area.'})
        clean.append(
            {
                'domain': row['domain'],
                'importance': _key,
                'level': str(level),
                'benchmark': str(benchmark) if benchmark is not None else None,
            }
        )
    missing = [domain.label for domain in domains if domain.key not in seen]
    if missing:
        raise ValidationError({'detail': f'Rate every skill area. Still needed: {", ".join(missing)}.'})
    return clean


# ---- CSV import ------------------------------------------------------------------------------------


def import_programs(upload, *, user, commit):
    """Dry run (commit=False) previews every row; commit applies them only when no row has an error.

    New programs are created switched off. Existing programs get their descriptive fields updated; their
    activation, profile and verification never change through an import.
    """
    if upload is None:
        raise ValidationError({'file': 'Choose a CSV file.'})
    if upload.size > settings.CATALOG_IMPORT_MAX_BYTES:
        raise ValidationError({'file': 'The file is larger than 1 MB.'})
    try:
        text = upload.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValidationError({'file': 'Save the file as UTF-8 CSV and try again.'}) from exc
    reader = csv.DictReader(io.StringIO(text))
    headers = [str(name or '').strip() for name in reader.fieldnames or []]
    missing = [name for name in REQUIRED_IMPORT_COLUMNS if name not in headers]
    unknown = [name for name in headers if name not in IMPORT_COLUMNS]
    if missing or unknown:
        raise ValidationError({'file': f'Columns must be {", ".join(IMPORT_COLUMNS)}. Missing: {", ".join(missing) or "none"}; unknown: {", ".join(unknown) or "none"}.'})
    rows = list(reader)
    if len(rows) > settings.CATALOG_IMPORT_MAX_ROWS:
        raise ValidationError({'file': f'Import at most {settings.CATALOG_IMPORT_MAX_ROWS} rows at a time.'})
    existing = {row.code: row for row in CollegeProgram.objects.all()}
    preview = []
    seen = set()
    for number, raw in enumerate(rows, start=2):
        data = {key.strip(): (value or '').strip() for key, value in raw.items() if key}
        entry = {'line': number, 'code': data.get('code', ''), 'name': data.get('name', ''), 'action': '', 'errors': []}
        try:
            code = _code(data.get('code'))
            if code in seen:
                raise ValidationError({'code': 'This code appears twice in the file.'})
            seen.add(code)
            _family(data.get('family'))
            for field in PROGRAM_TEXT_FIELDS:
                _text(data, field, required=field == 'name')
            _url(data.get('source_url'))
            _date(data.get('verified_on'))
            entry['action'] = 'update' if code in existing else 'create'
        except ValidationError as exc:
            entry['errors'] = [str(message) for messages in exc.detail.values() for message in messages]
        preview.append(entry)
    errors = sum(1 for entry in preview if entry['errors'])
    if commit:
        if errors:
            raise ValidationError({'file': f'{errors} row(s) have errors. Fix them and run the dry run again.'})
        with transaction.atomic():
            for raw, entry in zip(rows, preview):
                data = {key.strip(): (value or '').strip() for key, value in raw.items() if key}
                program = existing.get(entry['code'].lower())
                if program is None:
                    program = create_program(data, user=user)
                    existing[program.code] = program
                else:
                    update_program(program, {key: value for key, value in data.items() if key in (*PROGRAM_TEXT_FIELDS, 'source_url', 'family')}, user=user)
        audit.record(
            user=user,
            action='college_catalog_imported',
            summary=f'College catalog imported: {len(preview)} row(s)',
            target_type='CollegeProgram',
            details={'created': sum(1 for row in preview if row['action'] == 'create'), 'updated': sum(1 for row in preview if row['action'] == 'update')},
        )
    return {'rows': preview, 'errors': errors, 'committed': bool(commit)}


# ---- Interest instrument ----------------------------------------------------------------------------


def activate_instrument(instrument, *, user, license_confirmed):
    if license_confirmed is not True:
        raise ValidationError({'license_confirmed': 'Confirm that the license terms and attribution were reviewed.'})
    letters = set(
        InterestQuestion.objects.filter(instrument=instrument, is_active=True).values_list('riasec', flat=True)
    )
    if set(RIASEC_ORDER) - letters:
        raise ValidationError({'detail': 'This version does not cover all six interest types, so it cannot be used.'})
    now = timezone.now()
    try:
        with transaction.atomic():
            InterestInstrument.objects.filter(active_marker=InterestInstrument.ACTIVE).exclude(pk=instrument.pk).update(active_marker=None)
            instrument.active_marker = InterestInstrument.ACTIVE
            instrument.activated_at = now
            instrument.license_confirmed_at = now
            instrument.license_confirmed_by = user
            instrument.save(update_fields=['active_marker', 'activated_at', 'license_confirmed_at', 'license_confirmed_by'])
    except IntegrityError as exc:
        raise ValidationError({'detail': 'Another version was activated at the same moment. Reload and try again.'}) from exc
    audit.record(
        user=user,
        action='interest_instrument_activated',
        summary=f'Interest assessment activated: {instrument}',
        target_type='InterestInstrument',
        target_id=instrument.pk,
    )
    return instrument
