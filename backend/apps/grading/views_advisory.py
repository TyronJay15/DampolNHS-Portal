from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTeacher
from apps.grading.advisory import advisory_snapshot, term_subject_ids
from apps.grading.release import (
    ReleaseError,
    hide_student_card,
    roster_entry,
    show_ready_cards,
    show_student_card,
    student_can_show,
)
from apps.people.assignment_access import adviser_assignment_for
from apps.school.models import Term

ALL_TERMS = 'all'


def _advisory_term(user, assignment_id, term_id):
    assignment = adviser_assignment_for(user, assignment_id)
    if assignment is None:
        raise ReleaseError('Only the section adviser can do that.', status=403)
    term = get_object_or_404(Term, pk=term_id, school_year=assignment.school_year)
    return assignment, term


def _advisory_terms(user, assignment_id, term_id):
    """One term, or with term "all" every term of the year in which the section has a scheduled subject."""
    if term_id != ALL_TERMS:
        assignment, term = _advisory_term(user, assignment_id, term_id)
        return assignment, [term]
    assignment = adviser_assignment_for(user, assignment_id)
    if assignment is None:
        raise ReleaseError('Only the section adviser can do that.', status=403)
    terms = [
        term
        for term in Term.objects.filter(school_year=assignment.school_year).order_by('number')
        if term_subject_ids(assignment.section, term)
    ]
    return assignment, terms


def _roster_student(assignment, student_id):
    if student_id in (None, ''):
        raise ReleaseError('Choose one student.', status=400)
    placement = roster_entry(assignment.section, student_id)
    if placement is None:
        raise ReleaseError('That student is not in this advisory section.', status=404)
    return placement.student


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
            assignment, terms = _advisory_terms(request.user, request.data.get('assignment'), request.data.get('term'))
            student = _roster_student(assignment, request.data.get('student'))
            moved = 0
            for term in terms:
                if student_can_show(assignment.section, term, student):
                    moved += show_student_card(section=assignment.section, term=term, student=student, user=request.user)
            if not moved:
                raise ReleaseError('No approved grades to show yet.')
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({'shown': moved, 'terms': [term.label for term in terms]})


class HideGradesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, terms = _advisory_terms(request.user, request.data.get('assignment'), request.data.get('term'))
            student = _roster_student(assignment, request.data.get('student'))
            moved = sum(
                hide_student_card(section=assignment.section, term=term, student=student, user=request.user)
                for term in terms
            )
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({'hidden': moved, 'terms': [term.label for term in terms]})


class ShowReadyView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        try:
            assignment, terms = _advisory_terms(request.user, request.data.get('assignment'), request.data.get('term'))
            result = {'shown': 0, 'skipped': 0}
            for term in terms:
                done = show_ready_cards(section=assignment.section, term=term, user=request.user)
                result = {key: result[key] + done[key] for key in result}
        except ReleaseError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        return Response({**result, 'terms': [term.label for term in terms]})
