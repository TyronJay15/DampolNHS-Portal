from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.school.models import Program, Subject
from apps.school.serializers import AdminProgramSerializer, SubjectSerializer


class AdminProgramListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        programs = Program.objects.all().prefetch_related('program_subjects__subject')
        subjects = Subject.objects.filter(is_active=True)
        return Response(
            {
                'programs': AdminProgramSerializer(programs, many=True).data,
                'subjects': SubjectSerializer(subjects, many=True).data,
            }
        )

    def post(self, request):
        serializer = AdminProgramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        program = serializer.save()
        audit.record(
            user=request.user,
            action='cms_save',
            summary=f'Created program {program.code}',
            target_type='Program',
            target_id=program.id,
        )
        return Response(serializer.data, status=201)


class AdminProgramDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        program = get_object_or_404(Program, pk=pk)
        serializer = AdminProgramSerializer(program, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record(
            user=request.user,
            action='cms_save',
            summary=f'Updated program {program.code}',
            target_type='Program',
            target_id=program.id,
        )
        return Response(serializer.data)


class AdminSubjectCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        code = slugify(request.data.get('code') or '')
        name = str(request.data.get('name') or '').strip()
        if not code or not name:
            return Response({'detail': 'Subject code and name are required.'}, status=400)
        if Subject.objects.filter(code=code).exists():
            return Response({'detail': 'A subject with that code already exists.'}, status=400)
        subject = Subject.objects.create(code=code, name=name, is_active=True)
        return Response(SubjectSerializer(subject).data, status=201)
