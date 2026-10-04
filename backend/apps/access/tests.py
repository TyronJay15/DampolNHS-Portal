from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access.models import AccessRequest, AccessTag
from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.grading.models import CorrectionRequest, Grade
from apps.notifications.models import Notification
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.people.tests_access import make_programs
from apps.school.models import ProgramSubject, SchoolYear, Section, Subject, Term
from apps.school.term_plan import TermPlan, seed_year_plan
from apps.cms.models import Announcement, SiteContent

IN_A_MONTH = str(timezone.localdate() + timedelta(days=30))


def _user(email, role, **extra):
    return User.objects.create_user(
        email=email, password='Strongpass1', first_name=email.split('@')[0].title(), last_name='Cruz', role=role,
        approval_status=User.ApprovalStatus.APPROVED, **extra,
    )


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class AccessBase(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.programs = make_programs()
        self.admin = _user('admin@x.com', User.Role.ADMIN)
        self.head = _user('head@x.com', User.Role.HEAD_TEACHER)
        self.teacher = _user('tina@x.com', User.Role.TEACHER)
        self.other_teacher = _user('omar@x.com', User.Role.TEACHER)
        self.student_user = _user('ana@x.com', User.Role.STUDENT)
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000000001', grade_level='Grade 11')

    def grant(self, owner, holder, activity, **extra):
        body = {'holder': holder.id, 'activity': activity, 'ends_on': IN_A_MONTH, **extra}
        return _client(owner).post('/api/access/tags/', body, format='json')

    def submit(self, user, activity, payload, note='Ready to go'):
        return _client(user).post(
            '/api/access/requests/', {'activity': activity, 'payload': payload, 'note': note}, format='json'
        )

    def decide(self, owner, request_id, approve=True, note=''):
        return _client(owner).post(
            f'/api/access/requests/{request_id}/decide/', {'approve': approve, 'note': note}, format='json'
        )


class TagRulesTests(AccessBase):
    def test_owner_must_set_an_end_date_or_choose_no_end_date(self):
        missing = self.grant(self.admin, self.head, 'review_registrations', ends_on='')
        self.assertEqual(missing.status_code, 400)
        past = self.grant(self.admin, self.head, 'review_registrations', ends_on='2020-01-01')
        self.assertEqual(past.status_code, 400)
        open_ended = self.grant(self.admin, self.head, 'review_registrations', ends_on='', no_end_date=True)
        self.assertEqual(open_ended.status_code, 201, open_ended.data)
        self.assertIsNone(open_ended.data['ends_on'])
        self.assertTrue(AuditLog.objects.filter(action='access_tag_granted', family='access').exists())
        self.assertTrue(Notification.objects.filter(user=self.head, category='access').exists())

    def test_only_the_owner_role_tags_and_only_the_holder_roles_are_tagged(self):
        self.assertEqual(self.grant(self.head, self.teacher, 'review_registrations').status_code, 403)
        self.assertEqual(self.grant(self.admin, self.student_user, 'review_registrations').status_code, 400)
        self.assertEqual(self.grant(self.admin, self.admin, 'review_registrations').status_code, 400)
        self.assertEqual(self.grant(self.head, self.head, 'prepare_placements').status_code, 400)
        self.assertEqual(self.grant(self.teacher, self.other_teacher, 'prepare_placements').status_code, 403)
        self.assertEqual(self.grant(self.head, self.teacher, 'prepare_placements').status_code, 201)

    def test_admin_can_tag_a_teacher_who_works_from_the_teacher_area(self):
        tagged = self.grant(self.admin, self.teacher, 'review_registrations')
        self.assertEqual(tagged.status_code, 201, tagged.data)
        self.assertEqual(tagged.data['work_path'], '/teacher/access/registrations')
        self.assertEqual(tagged.data['holder']['role_label'], 'Teacher')
        holders = _client(self.admin).get('/api/access/overview/').data['owns'][0]['holders']
        self.assertEqual({person['role'] for person in holders}, {'head_teacher', 'teacher'})
        self.assertEqual(_client(self.teacher).get('/api/admin/registrations/').status_code, 200)

    def test_one_live_tag_per_person_and_activity(self):
        self.grant(self.admin, self.head, 'edit_programs')
        self.assertEqual(self.grant(self.admin, self.head, 'edit_programs').status_code, 400)

    def test_head_teacher_tags_only_within_their_grade_levels(self):
        TeacherAssignment.objects.create(
            teacher=self.head, assignment_type=TeacherAssignment.Type.HEAD_TEACHER,
            school_year=self.year, grade_level='Grade 11',
        )
        self.assertEqual(self.grant(self.head, self.teacher, 'prepare_placements', scope='Grade 12').status_code, 400)
        self.assertEqual(self.grant(self.head, self.teacher, 'prepare_placements', scope='Grade 11').status_code, 201)

    def test_closing_needs_a_reason_and_cancels_waiting_requests(self):
        tag_id = self.grant(self.admin, self.head, 'review_registrations').data['id']
        reg = Registration.objects.create(
            user=self.student_user, school_year=self.year, program=self.programs['STEMC'],
            grade_level_enrollment='Grade 11',
        )
        self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [reg.id]})
        url = f'/api/access/tags/{tag_id}/close/'
        self.assertEqual(_client(self.admin).post(url, {'reason': ''}, format='json').status_code, 400)
        closed = _client(self.admin).post(url, {'reason': 'Enrollment period over'}, format='json')
        self.assertEqual(closed.status_code, 200, closed.data)
        self.assertEqual(closed.data['state'], 'closed')
        self.assertEqual(AccessRequest.objects.get().status, AccessRequest.Status.WITHDRAWN)
        self.assertEqual(_client(self.head).get('/api/admin/registrations/').status_code, 403)

    def test_ended_tags_stop_working(self):
        self.grant(self.admin, self.head, 'review_registrations')
        AccessTag.objects.update(ends_on=timezone.localdate() - timedelta(days=1))
        self.assertEqual(_client(self.head).get('/api/admin/registrations/').status_code, 403)

    def test_students_are_refused_everywhere(self):
        client = _client(self.student_user)
        for url in ('/api/access/overview/', '/api/access/tags/', '/api/access/requests/'):
            self.assertEqual(client.get(url).status_code, 403)


class RegistrationReviewFlowTests(AccessBase):
    def setUp(self):
        super().setUp()
        self.grant(self.admin, self.head, 'review_registrations')
        self.reg = Registration.objects.create(
            user=self.student_user, school_year=self.year, program=self.programs['STEMC'],
            grade_level_enrollment='Grade 11',
        )

    def test_tagged_head_teacher_reads_pending_but_cannot_act_directly(self):
        listed = _client(self.head).get('/api/admin/registrations/', {'status': 'approved'})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row['id'] for row in listed.data['results']], [self.reg.id])
        direct = _client(self.head).post(f'/api/admin/registrations/{self.reg.id}/approve/')
        self.assertEqual(direct.status_code, 403)

    def test_request_waits_then_the_admin_approves_and_it_is_applied(self):
        sent = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]})
        self.assertEqual(sent.status_code, 201, sent.data)
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, Registration.Status.PENDING)
        inbox = _client(self.admin).get('/api/access/requests/', {'box': 'inbox'}).data
        self.assertEqual([row['id'] for row in inbox], [sent.data['id']])
        self.assertEqual(self.decide(self.head, sent.data['id']).status_code, 403)
        done = self.decide(self.admin, sent.data['id'])
        self.assertEqual(done.data['status'], 'approved', done.data)
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, Registration.Status.APPROVED)
        self.assertEqual(self.reg.reviewed_by, self.admin)
        actions = set(AuditLog.objects.values_list('action', flat=True))
        self.assertTrue({'access_request_submitted', 'access_request_approved', 'account_approved'} <= actions)

    def test_rejecting_needs_a_reason_and_declining_needs_one_too(self):
        no_reason = self.submit(self.head, 'review_registrations', {'decision': 'reject', 'registrations': [self.reg.id]})
        self.assertEqual(no_reason.status_code, 400)
        no_note = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]}, note='')
        self.assertEqual(no_note.status_code, 400)
        sent = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]})
        self.assertEqual(self.decide(self.admin, sent.data['id'], approve=False).status_code, 400)
        declined = self.decide(self.admin, sent.data['id'], approve=False, note='Documents missing')
        self.assertEqual(declined.data['status'], 'declined')
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, Registration.Status.PENDING)

    def test_changed_data_marks_the_request_failed_instead_of_applying(self):
        sent = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]})
        Registration.objects.filter(pk=self.reg.pk).update(status=Registration.Status.REJECTED)
        result = self.decide(self.admin, sent.data['id'])
        self.assertEqual(result.data['status'], 'failed')
        self.assertTrue(AuditLog.objects.filter(action='access_request_failed').exists())

    def test_proposer_can_withdraw_and_unanswered_requests_expire(self):
        first = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]})
        withdrawn = _client(self.head).post(f'/api/access/requests/{first.data["id"]}/withdraw/')
        self.assertEqual(withdrawn.data['status'], 'withdrawn')
        second = self.submit(self.head, 'review_registrations', {'decision': 'approve', 'registrations': [self.reg.id]})
        AccessRequest.objects.filter(pk=second.data['id']).update(expires_at=timezone.now() - timedelta(minutes=1))
        mine = _client(self.head).get('/api/access/requests/', {'box': 'mine'}).data
        self.assertEqual({row['id']: row['status'] for row in mine}[second.data['id']], 'expired')


class TeacherActivitiesTests(AccessBase):
    def setUp(self):
        super().setUp()
        self.section = Section.objects.create(
            school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC']
        )
        self.g12 = Section.objects.create(
            school_year=self.year, name='STEM-A', grade_level='Grade 12', program=self.programs['STEM']
        )
        Registration.objects.create(
            user=self.student_user, school_year=self.year, program=self.programs['STEMC'],
            grade_level_enrollment='Grade 11', status=Registration.Status.APPROVED,
        )

    def test_placements_are_read_in_scope_proposed_and_applied_by_the_head_teacher(self):
        self.grant(self.head, self.teacher, 'prepare_placements', scope='Grade 11')
        listed = _client(self.teacher).get('/api/admin/placements/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual({row['grade_level'] for row in listed.data}, {'Grade 11'})
        outside = self.submit(self.teacher, 'prepare_placements', {'section': self.g12.id, 'students': [self.student.id]})
        self.assertEqual(outside.status_code, 400)
        sent = self.submit(self.teacher, 'prepare_placements', {'section': self.section.id, 'students': [self.student.id]})
        self.assertEqual(sent.status_code, 201, sent.data)
        self.assertFalse(StudentSection.objects.exists())
        self.assertEqual(self.decide(self.head, sent.data['id']).data['status'], 'approved')
        self.assertTrue(StudentSection.objects.filter(student=self.student, section=self.section).exists())

    def test_assignment_and_term_plan_proposals_are_applied(self):
        subject = Subject.objects.create(code='gen-math', name='General Mathematics')
        ProgramSubject.objects.create(program=self.programs['STEMC'], subject=subject, kind='core', terms=[1])
        seed_year_plan(self.year)
        self.grant(self.head, self.teacher, 'prepare_assignments')
        self.grant(self.head, self.teacher, 'prepare_term_plan')
        duty = self.submit(self.teacher, 'prepare_assignments', {
            'type': 'subject_teacher', 'section': self.section.id, 'teacher': self.other_teacher.id, 'subject': subject.id,
        })
        self.assertEqual(self.decide(self.head, duty.data['id']).data['status'], 'approved')
        self.assertTrue(TeacherAssignment.objects.filter(teacher=self.other_teacher, subject=subject).exists())
        plan = self.submit(self.teacher, 'prepare_term_plan', {
            'school_year': self.year.id,
            'rows': [{'program': self.programs['STEMC'].id, 'subject': subject.id, 'terms': [1, 2]}],
        })
        self.assertEqual(plan.status_code, 201, plan.data)
        self.assertEqual(self.decide(self.head, plan.data['id']).data['status'], 'approved')
        self.assertEqual(TermPlan(self.year.id).terms_for(self.programs['STEMC'].id, subject.id), [1, 2])

    def test_a_teacher_cannot_review_their_own_correction(self):
        term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        subject = Subject.objects.create(code='gen-sci', name='General Science')
        grade = Grade.objects.create(
            student=self.student, subject=subject, term=term, school_year=self.year, section=self.section,
            score=Decimal('80.00'), status=Grade.Status.APPROVED, teacher=self.teacher,
        )
        own = CorrectionRequest.objects.create(
            grade=grade, requested_by=self.teacher, current_score=Decimal('80.00'),
            proposed_score=Decimal('85.00'), reason='Typo',
        )
        self.grant(self.head, self.teacher, 'review_corrections')
        refused = self.submit(self.teacher, 'review_corrections', {'correction': own.id, 'decision': 'approved'})
        self.assertEqual(refused.status_code, 400)
        listed = _client(self.teacher).get('/api/grades/corrections/', {'review': 1}).data
        self.assertEqual(listed, [])

    def test_placement_request_shows_before_and_after(self):
        self.grant(self.head, self.teacher, 'prepare_placements')
        sent = self.submit(self.teacher, 'prepare_placements', {'section': self.section.id, 'students': [self.student.id]})
        self.assertEqual(sent.data['changes'][0]['before'], 'Not placed')
        self.assertIn('STEMC-A', sent.data['changes'][0]['after'])

    def test_edit_program_proposal_is_applied_by_the_admin(self):
        self.grant(self.admin, self.head, 'edit_programs')
        sent = self.submit(self.head, 'edit_programs', {
            'program': self.programs['STEMC'].id, 'changes': {'summary': 'New summary', 'code': 'HACK'},
        })
        self.assertEqual(sent.status_code, 201, sent.data)
        self.assertEqual(sent.data['summary'], 'Edit STEMC: Summary')
        self.assertEqual(sent.data['changes'][0]['after'], 'New summary')
        self.assertEqual(self.decide(self.admin, sent.data['id']).data['status'], 'approved')
        self.programs['STEMC'].refresh_from_db()
        self.assertEqual((self.programs['STEMC'].summary, self.programs['STEMC'].code), ('New summary', 'STEMC'))


class WebsiteActivitiesTests(AccessBase):
    def setUp(self):
        super().setUp()
        SiteContent.objects.create(document='about', payload={'mission': 'Old mission', 'vision': 'Old vision'})

    def propose_about(self, changes, **extra):
        return self.submit(self.teacher, 'edit_website_pages', {'document': 'about', 'changes': changes, **extra})

    def test_page_tag_is_limited_to_its_page(self):
        tagged = self.grant(self.admin, self.teacher, 'edit_website_pages', scope='about')
        self.assertEqual(tagged.status_code, 201, tagged.data)
        self.assertEqual(tagged.data['scope_text'], 'About')
        self.assertEqual(self.grant(self.admin, self.head, 'edit_website_pages', scope='Grade 11').status_code, 400)
        outside = self.submit(self.teacher, 'edit_website_pages', {'document': 'landing', 'changes': {'heroTitle': 'Hi'}})
        self.assertEqual(outside.status_code, 400)

    def test_page_change_shows_before_and_after_and_merges_on_approval(self):
        self.grant(self.admin, self.teacher, 'edit_website_pages')
        # A 'before' sent by the browser is ignored; the server takes its own snapshot.
        sent = self.propose_about({'mission': 'New mission'}, before={'mission': 'forged'})
        self.assertEqual(sent.status_code, 201, sent.data)
        self.assertEqual(sent.data['changes'], [{'label': 'Mission', 'before': 'Old mission', 'after': 'New mission'}])
        self.assertEqual(SiteContent.objects.get(document='about').payload['mission'], 'Old mission')
        self.assertEqual(self.decide(self.admin, sent.data['id']).data['status'], 'approved')
        page = SiteContent.objects.get(document='about').payload
        self.assertEqual((page['mission'], page['vision']), ('New mission', 'Old vision'))

    def test_a_field_the_admin_changed_meanwhile_is_not_overwritten(self):
        self.grant(self.admin, self.teacher, 'edit_website_pages')
        sent = self.propose_about({'mission': 'Teacher mission'})
        SiteContent.objects.filter(document='about').update(payload={'mission': 'Admin mission', 'vision': 'Old vision'})
        result = self.decide(self.admin, sent.data['id'])
        self.assertEqual(result.data['status'], 'failed')
        self.assertIn('Mission', result.data['result']['error'])
        self.assertEqual(SiteContent.objects.get(document='about').payload['mission'], 'Admin mission')

    def test_unused_uploaded_photo_is_deleted_when_the_request_is_declined(self):
        from unittest import mock

        self.grant(self.admin, self.teacher, 'edit_website_pages')
        sent = self.propose_about({'heroImage': '/media/cms/new-photo.jpg'})
        with mock.patch('apps.cms.services.default_storage') as storage:
            storage.exists.return_value = True
            self.decide(self.admin, sent.data['id'], approve=False, note='Not this photo')
        storage.delete.assert_called_once_with('cms/new-photo.jpg')

    def test_news_create_update_and_delete_go_through_the_admin(self):
        self.grant(self.admin, self.head, 'post_news')
        self.assertEqual(self.grant(self.admin, self.teacher, 'post_news', scope='about').status_code, 400)
        created = self.submit(self.head, 'post_news', {
            'action': 'create', 'fields': {'title': 'Sports fest', 'body': 'Join us', 'kind': 'news', 'is_published': True},
        })
        self.assertEqual(created.status_code, 201, created.data)
        self.assertFalse(Announcement.objects.exists())
        self.assertEqual(self.decide(self.admin, created.data['id']).data['status'], 'approved')
        post = Announcement.objects.get()
        self.assertTrue(post.is_published)
        hidden = self.submit(self.head, 'post_news', {'action': 'update', 'announcement': post.id, 'fields': {'is_published': False}})
        self.assertEqual(hidden.data['changes'], [{'label': 'Is published', 'before': 'Yes', 'after': 'No'}])
        self.assertEqual(self.decide(self.admin, hidden.data['id']).data['status'], 'approved')
        removed = self.submit(self.head, 'post_news', {'action': 'delete', 'announcement': post.id})
        self.assertEqual(removed.data['summary'], 'Delete "Sports fest"')
        self.assertTrue(Announcement.objects.exists())
        self.assertEqual(self.decide(self.admin, removed.data['id']).data['status'], 'approved')
        self.assertFalse(Announcement.objects.exists())

    def test_tagged_people_see_drafts_and_can_upload_but_not_delete_live_photos(self):
        Announcement.objects.create(title='Draft', body='x', image='/media/cms/live.jpg', is_published=False)
        self.grant(self.admin, self.teacher, 'post_news')
        client = _client(self.teacher)
        self.assertEqual(len(client.get('/api/announcements/').data), 1)
        self.assertEqual(len(_client(self.other_teacher).get('/api/announcements/').data), 0)
        denied = client.delete('/api/cms/media/', {'url': '/media/cms/live.jpg'}, format='json')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(_client(self.other_teacher).post('/api/cms/media/', {}).status_code, 403)
