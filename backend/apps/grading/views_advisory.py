from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTeacher
from apps.grading.advisory import advisory_snapshot
from apps.grading.release import (
    ReleaseError,
    hide_student_card,
    roster_entry,
    set_ptpa,
    set_ptpa_bulk,
    show_ready_cards,
    show_student_card,
)
from apps.people.assignment_access import adviser_assignment_for
from apps.school.models import Term


def _advisory_term(user, assignment_id, term_id):
    assignment = adviser_assignment_for(user, assignment_id)
    if assignment is None:
        raise ReleaseError('Only the section adviser can do that.', status=403)
    term = get_object_or_404(Term, pk=term_id, school_year=assignment.school_year)
    return assignment, term


def _advisory_context(user, assignment_id, term_id, student_id):
    assignment, term = _advisory_term(user, assignment_id, term_id)
    if student_id in (None, ''):
        raise ReleaseError('Choose one student.', status=400)
    placement = roster_entry(assignment.section, student_id)
    if placement is None:
        raise ReleaseError('That student is not in this advisory section.', status=404)
    return assignment, term, placement.student


class AdvisoryGradesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        assignment = adviser_assignment_for(request.user, request.query_params.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You are not the adviser for that section.'}, status=403)
        term = get_object_or_404(Term, pk=request.query_params.get('term'), school_year=assignment.school_year)
        snapshot = advisory_snapshot(assignment.section, term)
        from apps.school.labels import section_label

        snapshot['assignment'] = {
            'id': assignment.id,
            'section': section_label(assignment.section),
            'school_year': assignment.school_year.label,
        }
        return Response(snapshot)


class ShowGradesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, term, student = _advisory_context(
                request.user,
                request.data.get('assignment'),
                request.data.get('term'),
                request.data.get('student'),
            )
            moved = show_student_card(
                section=assignment.section,
                term=term,
                student=student,
                user=request.user,
            )
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({'shown': moved})


class HideGradesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, term, student = _advisory_context(
                request.user,
                request.data.get('assignment'),
                request.data.get('term'),
                request.data.get('student'),
            )
            moved = hide_student_card(
                section=assignment.section,
                term=term,
                student=student,
                user=request.user,
            )
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({'hidden': moved})


class PtpaAttendanceView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, term, student = _advisory_context(
                request.user,
                request.data.get('assignment'),
                request.data.get('term'),
                request.data.get('student'),
            )
            hidden = set_ptpa(
                section=assignment.section,
                term=term,
                student=student,
                attended=bool(request.data.get('attended')),
                user=request.user,
            )
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({'attended': bool(request.data.get('attended')), 'hidden': hidden})


class PtpaBulkView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, term = _advisory_term(
                request.user,
                request.data.get('assignment'),
                request.data.get('term'),
            )
            result = set_ptpa_bulk(
                section=assignment.section,
                term=term,
                student_ids=request.data.get('students'),
                attended=bool(request.data.get('attended')),
                user=request.user,
            )
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response(result)


class ShowReadyView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, term = _advisory_term(
                request.user,
                request.data.get('assignment'),
                request.data.get('term'),
            )
            result = show_ready_cards(section=assignment.section, term=term, user=request.user)
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response(result)
