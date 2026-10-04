from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import filter_levels, reading_levels, role_or_tagged
from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.school.models import Curriculum, Program, SkillDomain, Subject
from apps.school.programs import update_program
from apps.school.serializers import AdminProgramSerializer, SubjectSerializer


class AdminProgramListView(APIView):
    """Admins manage every program; a head teacher tagged to edit programs reads those in their levels."""

    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.ADMIN, 'edit_programs')]

    def get(self, request):
        programs = filter_levels(
            Program.objects.all().prefetch_related('program_subjects__subject'),
            reading_levels(request.user, 'edit_programs'),
        )
        subjects = Subject.objects.filter(is_active=True).select_related('skill_domain')
        return Response(
            {
                'programs': AdminProgramSerializer(programs, many=True).data,
                'subjects': SubjectSerializer(subjects, many=True).data,
                'curricula': list(Curriculum.objects.filter(is_active=True).values('code', 'name')),
                'skill_domains': list(SkillDomain.objects.filter(is_active=True).values('key', 'label')),
            }
        )

    def post(self, request):
        serializer = AdminProgramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        program = serializer.save()
        audit.record(
            user=request.user,
            action='program_created',
            summary=f'Created program {program.code}',
            target_type='Program',
            target_id=program.id,
        )
        return Response(serializer.data, status=201)


class AdminProgramDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        program = get_object_or_404(Program, pk=pk)
        return Response(update_program(program, request.data, request.user))


class AdminSubjectCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        code = slugify(request.data.get('code') or '')
        name = str(request.data.get('name') or '').strip()
        if not code or not name:
            return Response({'detail': 'Subject code and name are required.'}, status=400)
        if Subject.objects.filter(code=code).exists():
            return Response({'detail': 'A subject with that code already exists.'}, status=400)
        domain = None
        domain_key = str(request.data.get('skill_domain') or '').strip()
        if domain_key:
            domain = SkillDomain.objects.filter(key=domain_key, is_active=True).first()
            if domain is None:
                return Response({'detail': 'Unknown skill domain.'}, status=400)
        subject = Subject.objects.create(code=code, name=name, skill_domain=domain, is_active=True)
        return Response(SubjectSerializer(subject).data, status=201)
