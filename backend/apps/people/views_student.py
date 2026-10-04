from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile
from apps.accounts.permissions import IsStudent
from apps.audit import services as audit
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.people.serializers import StudentProfileUpdateSerializer
from apps.school.labels import section_label
from apps.school.models import SchoolYear
from apps.school.term_plan import scheduled_subject_payloads


def student_me_payload(user):
    profile = StudentProfile.objects.filter(user=user).first()
    if profile is None:
        return None

    registration = (
        Registration.objects.filter(user=user)
        .select_related('program', 'school_year')
        .first()
    )
    assignment = (
        StudentSection.objects.filter(student=profile, is_active=True)
        .select_related('section', 'section__program', 'school_year')
        .first()
    )
    section_payload = None
    if assignment:
        adviser = (
            TeacherAssignment.objects.filter(
                section=assignment.section,
                school_year=assignment.school_year,
                assignment_type=TeacherAssignment.Type.ADVISER,
                status=TeacherAssignment.Status.ACTIVE,
            )
            .select_related('teacher')
            .first()
        )
        teacher = adviser.teacher if adviser else None
        section_payload = {
            'name': assignment.section.name,
            'display_label': section_label(assignment.section),
            'grade_level': assignment.section.grade_level,
            'program': assignment.section.program.code if assignment.section.program_id else '',
            'school_year': assignment.school_year.label,
            'adviser': teacher.get_full_name() if teacher else '',
        }

    program = None
    if assignment and assignment.section.program_id:
        program = assignment.section.program
    elif registration:
        program = registration.program

    current_year = SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()
    school_year = ''
    if assignment:
        school_year = assignment.school_year.label
    elif current_year:
        school_year = current_year.label
    elif registration:
        school_year = registration.school_year.label

    return {
        'first_name': user.first_name,
        'middle_name': profile.middle_name,
        'last_name': user.last_name,
        'email': user.email,
        'lrn': profile.lrn,
        'grade_level': profile.grade_level,
        'birthdate': profile.birthdate.isoformat() if profile.birthdate else '',
        'gender': profile.gender,
        'contact_number': profile.contact_number,
        'address': profile.address,
        'guardian_name': profile.guardian_name,
        'guardian_contact': profile.guardian_contact,
        'program': registration.program.code if registration else '',
        'school_year': school_year,
        'section': section_payload,
        'subjects': scheduled_subject_payloads(program, assignment.school_year if assignment else current_year),
    }


class StudentMeView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        payload = student_me_payload(request.user)
        if payload is None:
            return Response({'detail': 'No student profile is linked to this account.'}, status=404)
        return Response(payload)

    def patch(self, request):
        profile = StudentProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response({'detail': 'No student profile is linked to this account.'}, status=404)

        serializer = StudentProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changed = []
        details = {}
        for field, value in serializer.validated_data.items():
            previous = getattr(profile, field)
            if previous != value:
                setattr(profile, field, value)
                changed.append(field)
                if field == 'gender':
                    details['gender'] = {'from': previous, 'to': value}

        if changed:
            profile.save(update_fields=[*changed, 'updated_at'])
            audit.record(
                user=request.user,
                action='student_profile_updated',
                summary=f'Updated profile details ({", ".join(changed)})',
                target_type='StudentProfile',
                target_id=profile.id,
                details={'changed': changed, **details},
            )

        return Response(student_me_payload(request.user))
