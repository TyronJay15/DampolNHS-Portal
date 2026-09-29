from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.grading.history import HEAD_TEACHER
from apps.grading.models import Grade
from apps.grading.progress import duty_queue_rows
from apps.grading.transitions import transition_grades
from apps.audit.catalog import GRADES
from apps.notifications.services import advisers_for_section, notify
from apps.school.labels import section_label
from apps.school.models import Term


def _teacher_tree(rows):
    teachers = {}
    for row in rows:
        teacher_id = row.get('teacher_id') or 0
        bucket = teachers.setdefault(
            teacher_id,
            {
                'teacher_id': row.get('teacher_id'),
                'teacher': row.get('teacher') or 'Unassigned teacher',
                'submitted': 0,
                'missing': 0,
                'sections': {},
            },
        )
        bucket['submitted'] += row.get('submitted') or 0
        bucket['missing'] += row.get('missing') or 0
        section_id = row.get('section_id') or 0
        section_bucket = bucket['sections'].setdefault(
            section_id,
            {
                'section_id': row.get('section_id'),
                'section': row.get('section') or 'Unassigned',
                'subjects': [],
            },
        )
        section_bucket['subjects'].append(row)
    tree = []
    for bucket in teachers.values():
        sections = []
        for section in bucket['sections'].values():
            section['submitted'] = sum(item.get('submitted') or 0 for item in section['subjects'])
            sections.append(section)
        sections.sort(key=lambda item: item['section'])
        tree.append(
            {
                'teacher_id': bucket['teacher_id'],
                'teacher': bucket['teacher'],
                'submitted': bucket['submitted'],
                'missing': bucket['missing'],
                'sections': sections,
            }
        )
    tree.sort(key=lambda item: (item['teacher'] or '').lower())
    return tree


class GradeQueueView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        term = get_object_or_404(Term.objects.select_related('school_year'), pk=request.query_params.get('term'))
        rows = duty_queue_rows(term)
        return Response(
            {
                'term': {'id': term.id, 'label': term.label, 'school_year': term.school_year.label},
                'groups': rows,
                'teachers': _teacher_tree(rows),
                'waiting': sum(row.get('submitted') or 0 for row in rows),
            }
        )


def _notify_advisers_of_approval(grades, term, actor):
    by_section = {}
    for row in grades:
        if not row.section_id:
            continue
        by_section.setdefault(row.section_id, {'section': row.section, 'students': set()})
        by_section[row.section_id]['students'].add(row.student_id)
    for payload in by_section.values():
        section = payload['section']
        shown = Grade.objects.filter(
            section=section,
            term=term,
            student_id__in=payload['students'],
            status=Grade.Status.RELEASED,
        ).exists()
        if not shown:
            continue
        notify(
            advisers_for_section(section),
            title=f'{term.label} · ready to re-show',
            body=(
                f'{actor.get_full_name()} approved new {term.label} grades for {section_label(section)}. '
                'Re-show to update student cards.'
            ),
            level='info',
            category=GRADES,
            action_path='/teacher/advisory',
        )


def _approve_pending(*, term, user, section_id=None, subject_id=None, teacher_id=None):
    pending_qs = Grade.objects.filter(term=term, status=Grade.Status.SUBMITTED).select_related(
        'teacher',
        'section',
        'section__program',
        'section__school_year',
    )
    if section_id:
        pending_qs = pending_qs.filter(section_id=section_id)
    if subject_id:
        pending_qs = pending_qs.filter(subject_id=subject_id)
    if teacher_id:
        pending_qs = pending_qs.filter(teacher_id=teacher_id)
    pending = list(pending_qs)
    teachers = {row.teacher for row in pending if row.teacher_id}
    moved = transition_grades(
        grades=pending,
        to_status=Grade.Status.APPROVED,
        user=user,
        reason='Head teacher approved grades',
        duty=HEAD_TEACHER,
    )
    if moved:
        audit.record(
            user=user,
            action='grades_approved',
            summary=f'Approved {moved} submitted grades for {term.label}',
            target_type='Term',
            target_id=term.id,
            details={
                'section_id': section_id,
                'subject_id': subject_id,
                'teacher_id': teacher_id,
            },
        )
        notify(
            teachers,
            title=f'{term.label} · grades approved',
            body=f'{user.get_full_name()} approved submitted grades for {term.label}.',
            level='success',
            category=GRADES,
            action_path='/teacher/classes',
        )
        _notify_advisers_of_approval(pending, term, user)
    return moved


class ApproveGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        moved = _approve_pending(
            term=term,
            user=request.user,
            section_id=request.data.get('section'),
            subject_id=request.data.get('subject'),
        )
        return Response({'approved': moved})


class ApproveTeacherGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        teacher_id = request.data.get('teacher')
        if not teacher_id:
            return Response({'detail': 'Choose a teacher.'}, status=400)
        get_object_or_404(User, pk=teacher_id, role=User.Role.TEACHER)
        moved = _approve_pending(term=term, user=request.user, teacher_id=teacher_id)
        return Response({'approved': moved})


class ApproveAllGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        moved = _approve_pending(term=term, user=request.user)
        return Response({'approved': moved})


class ReturnGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        section_id = request.data.get('section')
        subject_id = request.data.get('subject')
        shown = Grade.objects.filter(
            term=term,
            section_id=section_id,
            subject_id=subject_id,
            status=Grade.Status.RELEASED,
        ).count()
        grades = list(
            Grade.objects.filter(
                term=term,
                section_id=section_id,
                subject_id=subject_id,
                status__in=[Grade.Status.SUBMITTED, Grade.Status.APPROVED],
            )
        )
        if not grades:
            if shown:
                return Response(
                    {
                        'detail': (
                            f'{shown} shown card(s) were left untouched. '
                            'Hide those students first if you need their grades returned.'
                        )
                    },
                    status=400,
                )
            return Response({'detail': 'There are no submitted or approved grades to return.'}, status=400)
        moved = transition_grades(
            grades=grades,
            to_status=Grade.Status.DRAFT,
            user=request.user,
            reason='Head teacher returned grades',
            duty=HEAD_TEACHER,
        )
        audit.record(
            user=request.user,
            action='grades_returned',
            summary=f'Returned {moved} hidden grades to draft for {term.label}',
            target_type='Term',
            target_id=term.id,
            details={'still_shown': shown},
        )
        if moved:
            notify(
                {row.teacher for row in grades if row.teacher_id},
                title=f'{term.label} · grades returned',
                body=f'{request.user.get_full_name()} returned {term.label} grades to draft. Fix and submit again.',
                level='warning',
                category=GRADES,
                action_path='/teacher/classes',
            )
        return Response({'returned': moved, 'still_shown': shown})
