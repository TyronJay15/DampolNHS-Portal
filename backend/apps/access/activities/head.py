"""Activities a Head Teacher owns and can tag a Teacher to prepare (within the Head Teacher's levels)."""

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.access.activities.base import (
    HEAD_TEACHER,
    TEACHER,
    Activity,
    ActivityFailed,
    change,
    ids_from,
    names_text,
    require_level,
    short,
)
from apps.accounts.models import StudentProfile, User
from apps.grading.corrections import DECISIONS, CorrectionBlocked, review_correction
from apps.grading.models import CorrectionRequest
from apps.people.assignments import DutyRejected, create_assignment
from apps.people.models import StudentSection, TeacherAssignment
from apps.people.placement import current_year, place_student
from apps.school.labels import section_label
from apps.school.models import Program, SchoolYear, Section, Subject
from apps.school.term_plan import TermPlan
from apps.school.term_plan_edit import clean_rows, save_term_plan


def _current_section(section_id, tag):
    section = (
        Section.objects.filter(pk=section_id, archived_at__isnull=True, school_year__is_current=True)
        .select_related('program', 'school_year')
        .first()
    )
    if section is None:
        raise ValidationError({'detail': 'Choose a section of the current school year.'})
    require_level(tag, section.grade_level, section_label(section))
    return section


def _terms_text(terms):
    if not terms or len(terms) == 3:
        return 'All terms'
    return 'Term ' + ' & '.join(str(number) for number in terms)


class PreparePlacements(Activity):
    key = 'prepare_placements'
    label = 'Prepare placements'
    description = 'Propose placing or transferring students into sections.'
    owner_role = HEAD_TEACHER
    holder_roles = (TEACHER,)
    work_slug = 'placements'

    def clean(self, payload, tag, proposer):
        section = _current_section(payload.get('section'), tag)
        ids = ids_from(payload.get('students'), 'student', 60)
        if StudentProfile.objects.filter(pk__in=ids).count() != len(ids):
            raise ValidationError({'detail': 'One or more students no longer exist.'})
        return {'section': section.id, 'students': ids, 'transfer': bool(payload.get('transfer'))}

    def _students(self, cleaned):
        return StudentProfile.objects.filter(pk__in=cleaned['students']).select_related('user')

    def describe(self, cleaned):
        section = Section.objects.select_related('program').get(pk=cleaned['section'])
        names = [row.user.get_full_name() or row.lrn for row in self._students(cleaned)]
        verb = 'Transfer' if cleaned['transfer'] else 'Place'
        return short(f'{verb} {len(names)} student(s) into {section_label(section)}: {names_text(names)}')

    def diff(self, cleaned):
        section = Section.objects.select_related('program').get(pk=cleaned['section'])
        current = {
            row.student_id: section_label(row.section)
            for row in StudentSection.objects.filter(
                student_id__in=cleaned['students'], school_year=section.school_year, is_active=True
            ).select_related('section', 'section__program')
        }
        return [
            change(row.user.get_full_name() or row.lrn, current.get(row.id, 'Not placed'), section_label(section))
            for row in self._students(cleaned)
        ]

    def execute(self, cleaned, owner):
        year = current_year()
        section = Section.objects.select_related('program', 'school_year').get(pk=cleaned['section'])
        placed, failed = 0, []
        for student in self._students(cleaned):
            error = place_student(student, section, year, owner, transfer=cleaned['transfer'])
            if error:
                failed.append({'student': student.user.get_full_name(), 'error': error})
            else:
                placed += 1
        if not placed:
            raise ActivityFailed(failed[0]['error'] if failed else 'No student could be placed.')
        return {'placed': placed, 'failed': failed}


class PrepareTermPlan(Activity):
    key = 'prepare_term_plan'
    label = 'Prepare the term plan'
    description = 'Propose which terms each subject runs in.'
    owner_role = HEAD_TEACHER
    holder_roles = (TEACHER,)
    work_slug = 'term-plan'

    def clean(self, payload, tag, proposer):
        year = SchoolYear.objects.filter(pk=payload.get('school_year'), archived_at__isnull=True).first()
        if year is None:
            raise ValidationError({'detail': 'Choose a school year that is not archived.'})
        try:
            cleaned = clean_rows(payload.get('rows'), tag.granted_by)
        except (ValueError, PermissionDenied) as exc:
            raise ValidationError({'detail': str(getattr(exc, 'detail', exc))}) from exc
        for program in Program.objects.filter(pk__in={program_id for program_id, _subject in cleaned}):
            require_level(tag, program.grade_level, program.code)
        return {
            'school_year': year.id,
            'rows': [
                {'program': program_id, 'subject': subject_id, 'terms': terms}
                for (program_id, subject_id), terms in cleaned.items()
            ],
        }

    def describe(self, cleaned):
        year = SchoolYear.objects.get(pk=cleaned['school_year'])
        return f'Update the {year.label} term plan ({len(cleaned["rows"])} subject(s))'

    def diff(self, cleaned):
        rows = cleaned['rows']
        plan = TermPlan(cleaned['school_year'], program_ids={row['program'] for row in rows})
        programs = dict(Program.objects.filter(pk__in={row['program'] for row in rows}).values_list('id', 'code'))
        subjects = dict(Subject.objects.filter(pk__in={row['subject'] for row in rows}).values_list('id', 'name'))
        return [
            change(
                f'{programs.get(row["program"], "?")} · {subjects.get(row["subject"], "?")}',
                _terms_text(plan.terms_for(row['program'], row['subject'])),
                _terms_text(row['terms']),
            )
            for row in rows
        ]

    def execute(self, cleaned, owner):
        year = SchoolYear.objects.get(pk=cleaned['school_year'])
        try:
            return save_term_plan(year, cleaned['rows'], owner)
        except ValueError as exc:
            raise ActivityFailed(str(exc)) from exc


class PrepareAssignments(Activity):
    key = 'prepare_assignments'
    label = 'Prepare teacher assignments'
    description = 'Propose adviser or subject-teacher duties.'
    owner_role = HEAD_TEACHER
    holder_roles = (TEACHER,)
    work_slug = 'assignments'

    def clean(self, payload, tag, proposer):
        duty = payload.get('type')
        if duty not in (TeacherAssignment.Type.ADVISER, TeacherAssignment.Type.SUBJECT_TEACHER):
            raise ValidationError({'detail': 'Choose adviser or subject teacher.'})
        section = _current_section(payload.get('section'), tag)
        teacher = User.objects.filter(pk=payload.get('teacher'), role=TEACHER).first()
        if teacher is None:
            raise ValidationError({'detail': 'Choose a teacher.'})
        subject = None
        if duty == TeacherAssignment.Type.SUBJECT_TEACHER:
            subject = Subject.objects.filter(pk=payload.get('subject')).first()
            if subject is None:
                raise ValidationError({'detail': 'Choose a subject.'})
        return {'type': duty, 'section': section.id, 'teacher': teacher.id, 'subject': subject.id if subject else None}

    def _parts(self, cleaned):
        section = Section.objects.select_related('program', 'school_year').get(pk=cleaned['section'])
        teacher = User.objects.get(pk=cleaned['teacher'])
        subject = Subject.objects.get(pk=cleaned['subject']) if cleaned['subject'] else None
        return section, teacher.get_full_name() or teacher.email, subject

    def describe(self, cleaned):
        section, name, subject = self._parts(cleaned)
        if subject is None:
            return short(f'Make {name} adviser of {section_label(section)}')
        return short(f'Assign {name} to {subject.name} · {section_label(section)}')

    def diff(self, cleaned):
        section, name, subject = self._parts(cleaned)
        current = TeacherAssignment.objects.filter(
            section=section,
            school_year=section.school_year,
            assignment_type=cleaned['type'],
            status=TeacherAssignment.Status.ACTIVE,
            **({'subject': subject} if subject else {}),
        ).select_related('teacher').first()
        holder = (current.teacher.get_full_name() or current.teacher.email) if current else None
        return [change(f'{section_label(section)} · {subject.name if subject else "Adviser"}', holder, name)]

    def execute(self, cleaned, owner):
        try:
            return create_assignment(
                owner,
                teacher_id=cleaned['teacher'],
                assignment_type=cleaned['type'],
                section_id=cleaned['section'],
                subject_id=cleaned['subject'],
            )
        except DutyRejected as exc:
            raise ActivityFailed(str(exc)) from exc


class ReviewCorrections(Activity):
    key = 'review_corrections'
    label = 'Review correction requests'
    description = "Recommend approving or rejecting another teacher's grade correction."
    owner_role = HEAD_TEACHER
    holder_roles = (TEACHER,)
    work_slug = 'corrections'

    def clean(self, payload, tag, proposer):
        row = (
            CorrectionRequest.objects.filter(pk=payload.get('correction'))
            .select_related('grade__section', 'requested_by')
            .first()
        )
        if row is None or row.status != CorrectionRequest.Status.PENDING:
            raise ValidationError({'detail': 'That correction is no longer waiting for review.'})
        if row.requested_by_id == proposer.id:
            raise ValidationError({'detail': 'You cannot review your own correction request.'})
        if row.grade.section_id:
            require_level(tag, row.grade.section.grade_level, 'That correction')
        decision = payload.get('decision')
        if decision not in DECISIONS:
            raise ValidationError({'detail': 'Choose approve or reject.'})
        return {'correction': row.id, 'decision': decision, 'note': str(payload.get('note') or '').strip()[:255]}

    def _row(self, cleaned):
        return CorrectionRequest.objects.select_related(
            'grade__student__user', 'grade__subject', 'grade__section', 'requested_by'
        ).get(pk=cleaned['correction'])

    def describe(self, cleaned):
        row = self._row(cleaned)
        verb = 'Approve' if cleaned['decision'] == CorrectionRequest.Status.APPROVED else 'Reject'
        student = row.grade.student.user.get_full_name()
        return short(f'{verb} the correction for {student} · {row.grade.subject.name} ({row.grade.score} → {row.proposed_score})')

    def diff(self, cleaned):
        row = self._row(cleaned)
        approving = cleaned['decision'] == CorrectionRequest.Status.APPROVED
        after = row.proposed_score if approving else f'{row.grade.score} (correction rejected)'
        return [change(f'{row.grade.student.user.get_full_name()} · {row.grade.subject.name}', row.grade.score, after)]

    def execute(self, cleaned, owner):
        try:
            review_correction(self._row(cleaned), cleaned['decision'], cleaned['note'], owner)
        except CorrectionBlocked as exc:
            raise ActivityFailed(str(exc)) from exc
        return {'decision': cleaned['decision']}
