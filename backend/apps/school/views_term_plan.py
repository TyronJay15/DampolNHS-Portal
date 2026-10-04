"""The head teacher's term plan for a school year.

GET  /api/school-years/<id>/term-plan/   programs in the head teacher's grade levels, each subject with
                                         the terms it runs in and the terms that already hold grades
PUT  /api/school-years/<id>/term-plan/   {"rows": [{"program": id, "subject": id, "terms": [1, 2]}]}

Grades are never moved or deleted here. Saving a plan that leaves grades outside it is allowed;
the response counts them so the screen can say so, and those grades stay visible everywhere.
"""

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import reading_levels, role_or_tagged
from apps.accounts.models import User
from apps.school.models import SchoolYear
from apps.school.term_plan_edit import plan_payload, save_term_plan


PREPARE_TERM_PLAN = 'prepare_term_plan'


class TermPlanView(APIView):
    """Head teachers edit the plan; a teacher tagged to prepare it reads the plan for their levels."""

    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.HEAD_TEACHER, PREPARE_TERM_PLAN)]

    def get(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        return Response(plan_payload(year, reading_levels(request.user, PREPARE_TERM_PLAN)))

    def put(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        try:
            result = save_term_plan(year, request.data.get('rows'), request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response({**result, **plan_payload(year, reading_levels(request.user, PREPARE_TERM_PLAN))})
