"""Read payloads for the catalog, families and instruments. Input validation lives in the service modules."""

from apps.guidance.models import InterestQuestion
from apps.ml.models import CollegeProgram, CollegeProgramSkill


def family_payload(family, *, interest_types=None):
    payload = {'code': family.code, 'name': family.name, 'is_active': family.is_active}
    if interest_types is not None:
        payload['interest_types'] = interest_types
    return payload


def profile_rows(program):
    return [
        {
            'domain': skill.domain.key,
            'label': skill.domain.label,
            'level': str(skill.level),
            'benchmark': str(skill.minimum) if skill.minimum is not None else None,
            'official': skill.minimum_kind == CollegeProgramSkill.MinimumKind.OFFICIAL,
            'requirement_source': skill.requirement_source,
        }
        for skill in program.skills.all()
    ]


def program_payload(program, *, admin=False):
    payload = {
        'code': program.code,
        'name': program.name,
        'abbreviation': program.abbreviation,
        'family': family_payload(program.family) if program.family_id else None,
        'description': program.description,
        'career_overview': program.career_overview,
        'source': program.source,
        'source_url': program.source_url,
        'verified_on': program.verified_on,
        'verified': program.verification_status == CollegeProgram.Verification.VERIFIED,
        'profile_validated': program.profile_status == CollegeProgram.ProfileStatus.VALIDATED,
        'profile_version': program.profile_version,
        'profile': profile_rows(program),
        'strands': sorted({item.strand_group or item.code for item in program.shs_programs.all()}),
    }
    if admin:
        payload.update(
            {
                'id': program.pk,
                'is_active': program.is_active,
                'verified_by': program.verified_by.get_full_name() if program.verified_by_id else '',
                'shs_programs': sorted(item.code for item in program.shs_programs.all()),
            }
        )
    return payload


def instrument_payload(instrument, *, with_questions=False):
    payload = {
        'id': instrument.pk,
        'code': instrument.code,
        'version': instrument.version,
        'name': instrument.name,
        'source': instrument.source,
        'source_url': instrument.source_url,
        'license_url': instrument.license_url,
        'attribution': instrument.attribution,
        'active': instrument.active_marker is not None,
        'license_confirmed_at': instrument.license_confirmed_at,
        'pilot_status': instrument.pilot_status,
        'pilot_note': instrument.pilot_note,
    }
    if with_questions:
        payload['questions'] = [
            {
                'id': row.pk,
                'position': row.position,
                'text': row.text,
                'original_text': row.original_text,
                'change_note': row.change_note,
                'riasec': row.riasec,
            }
            for row in InterestQuestion.objects.filter(instrument=instrument, is_active=True).order_by('position')
        ]
    return payload
