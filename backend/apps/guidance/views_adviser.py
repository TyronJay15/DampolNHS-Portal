"""Adviser endpoints. Every request is checked against the adviser's own active assignment and student."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.audit import services as audit
from apps.guidance import adviser
from apps.guidance.consent import consent_state
from apps.guidance.permissions import IsGuidanceAdviser, advisee, adviser_assignment
from apps.guidance.recommendations import current_run, run_payload
from apps.guidance.selectors import latest_completed, latest_run, open_attempt
from apps.ml.models import CollegeOutcome
from apps.school.labels import section_label


def _section(assignment):
    return {
        'assignment_id': assignment.pk,
        'label': section_label(assignment.section),
        'grade_level': assignment.section.grade_level,
        'school_year': assignment.school_year.label,
    }


def _review(student):
    consents = consent_state(student)
    completed = latest_completed(student)
    return {
        'student': {'id': student.pk, 'name': student.user.get_full_name()},
        'consent': {'assessment': bool(consents['assessment']), 'training': bool(consents['training'])},
        'assessment': {
            'status': 'in_progress' if open_attempt(student) else 'completed' if completed else 'not_started',
            'completed_at': completed.completed_at if completed else None,
        },
        'recommendation': run_payload(current_run(student)),
        'notes': adviser.notes(student),
        'adviser_recommendations': adviser.recommendations(student),
        'outcome': adviser.outcome_payload(CollegeOutcome.objects.filter(student=student).select_related('college_program').first()),
    }


class AdvisoryGuidanceView(APIView):
    permission_classes = [IsGuidanceAdviser]

    def get(self, request, assignment_id):
        assignment = adviser_assignment(request.user, assignment_id)
        return Response({'section': _section(assignment), 'students': adviser.roster(assignment)})


class AdviseeView(APIView):
    permission_classes = [IsGuidanceAdviser]

    def get(self, request, assignment_id, student_id):
        assignment = adviser_assignment(request.user, assignment_id)
        student = advisee(assignment, student_id)
        audit.record(
            user=request.user,
            action='guidance_student_viewed',
            summary='Adviser opened a student\'s college recommendation',
            target_type='StudentProfile',
            target_id=student.pk,
        )
        return Response({'section': _section(assignment), **_review(student)})


class AdviseeWriteView(APIView):
    """Base for the adviser's writes: resolve the assignment and student, then act and return the review."""

    permission_classes = [IsGuidanceAdviser]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'

    def act(self, request, assignment, student):
        raise NotImplementedError

    def post(self, request, assignment_id, student_id):
        assignment = adviser_assignment(request.user, assignment_id)
        student = advisee(assignment, student_id)
        self.act(request, assignment, student)
        return Response({'section': _section(assignment), **_review(student)})


class AdviserNoteView(AdviseeWriteView):
    def act(self, request, assignment, student):
        adviser.add_note(student, request.data.get('body'), user=request.user)


class AdviserRecommendationView(AdviseeWriteView):
    def act(self, request, assignment, student):
        adviser.add_recommendation(student, request.data, user=request.user, run=latest_run(student))


class OutcomeView(AdviseeWriteView):
    def act(self, request, assignment, student):
        adviser.record_outcome(student, request.data, user=request.user, assignment=assignment)
