from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile
from apps.accounts.permissions import IsStudent
from apps.grading.student_card import student_grade_card


class StudentGradesView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        profile = StudentProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response({'detail': 'No student profile is linked to this account.'}, status=404)
        return Response(student_grade_card(profile))
