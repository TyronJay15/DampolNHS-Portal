"""Editing a program, shared by the Admin's Programs page and approved access requests."""

from apps.audit import services as audit
from apps.school.serializers import AdminProgramSerializer


def update_program(program, data, actor):
    """Apply a partial edit (details and subject list). Raises ValidationError for bad input."""
    serializer = AdminProgramSerializer(program, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    audit.record(
        user=actor,
        action='program_updated',
        summary=f'Updated program {program.code}',
        target_type='Program',
        target_id=program.id,
    )
    return serializer.data
