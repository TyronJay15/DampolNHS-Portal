"""Activities the Admin owns and can tag a Head Teacher or a Teacher to prepare."""

import json

from rest_framework.exceptions import ValidationError

from apps.access.activities.base import (
    ADMIN,
    HEAD_TEACHER,
    TEACHER,
    Activity,
    ActivityFailed,
    change,
    field_changes,
    humanize,
    ids_from,
    names_text,
    require_level,
    short,
)
from apps.accounts.models import User
from apps.cms.links import require_safe_links
from apps.cms.models import Announcement, SiteContent
from apps.cms.serializers import AnnouncementSerializer
from apps.cms.services import (
    delete_unused_uploads,
    live_document,
    save_announcement_changes,
    save_document,
    save_new_announcement,
    upload_urls,
)
from apps.guidance.catalog import IMPORTANCE_LABELS, _rating_fingerprint, _stored_fingerprint, clean_ratings, rating_round, save_ratings
from apps.ml.models import CollegeProgram
from apps.people.models import Registration
from apps.people.registrations import AlreadyReviewed, approve_registration, reject_registration
from apps.school.models import Program, Subject
from apps.school.programs import update_program
from apps.school.serializers import AdminProgramSerializer

PAGES = dict(SiteContent.Document.choices)
MAX_PAGE_CHANGE = 200_000


def _snapshot(payload, current):
    """The stored 'before' on approval; on submit the browser's copy was dropped, so take it fresh."""
    before = payload.get('before')
    return before if isinstance(before, dict) else current()


def _changed_since(before, live, keys):
    return [humanize(key) for key in keys if live.get(key) != before.get(key)]


class ReviewRegistrations(Activity):
    key = 'review_registrations'
    label = 'Review registrations'
    description = 'Recommend approving or rejecting pending student registrations.'
    owner_role = ADMIN
    holder_roles = (HEAD_TEACHER, TEACHER)
    work_slug = 'registrations'

    def clean(self, payload, tag, proposer):
        decision = payload.get('decision')
        if decision not in ('approve', 'reject'):
            raise ValidationError({'detail': 'Choose approve or reject.'})
        ids = ids_from(payload.get('registrations'), 'registration', 100)
        rows = list(Registration.objects.filter(pk__in=ids).select_related('user'))
        if len(rows) != len(ids):
            raise ValidationError({'detail': 'One or more registrations no longer exist.'})
        for row in rows:
            name = row.user.get_full_name() or row.user.email
            if row.status != Registration.Status.PENDING:
                raise ValidationError({'detail': f'{name} was already reviewed.'})
            require_level(tag, row.grade_level_enrollment, name)
        reason = str(payload.get('reason') or '').strip()[:500]
        if decision == 'reject' and not reason:
            raise ValidationError({'detail': 'A rejection reason is required.'})
        return {'decision': decision, 'registrations': ids, 'reason': reason}

    def _rows(self, cleaned):
        return Registration.objects.filter(pk__in=cleaned['registrations']).select_related('user')

    def describe(self, cleaned):
        names = [row.user.get_full_name() or row.user.email for row in self._rows(cleaned)]
        verb = 'Approve' if cleaned['decision'] == 'approve' else 'Reject'
        return short(f'{verb} {len(names)} registration(s): {names_text(names)}')

    def diff(self, cleaned):
        after = 'Approved' if cleaned['decision'] == 'approve' else f'Rejected: {cleaned["reason"]}'
        return [
            change(f'{row.user.get_full_name() or row.user.email} · {row.grade_level_enrollment}', 'Pending', after)
            for row in self._rows(cleaned)
        ]

    def execute(self, cleaned, owner):
        done = skipped = 0
        for row in self._rows(cleaned):
            try:
                if cleaned['decision'] == 'approve':
                    approve_registration(row, owner)
                else:
                    reject_registration(row, owner, cleaned['reason'])
                done += 1
            except AlreadyReviewed:
                skipped += 1
        if not done:
            raise ActivityFailed('Every registration in this request was already reviewed.')
        return {'done': done, 'skipped': skipped}


def _subjects_text(rows):
    names = dict(Subject.objects.filter(pk__in=[row.get('subject_id') or row.get('id') for row in rows]).values_list('id', 'name'))
    return ', '.join(
        f'{names.get(row.get("subject_id") or row.get("id"), "?")} ({row.get("kind") or "core"})' for row in rows
    )


class EditPrograms(Activity):
    key = 'edit_programs'
    label = 'Edit programs'
    description = "Propose changes to a program's summary, description, track, pathways and subject list."
    owner_role = ADMIN
    holder_roles = (HEAD_TEACHER, TEACHER)
    work_slug = 'programs'
    FIELDS = ('summary', 'description', 'track', 'pathways', 'subjects')

    def clean(self, payload, tag, proposer):
        program = Program.objects.filter(pk=payload.get('program')).first()
        if program is None:
            raise ValidationError({'detail': 'That program no longer exists.'})
        require_level(tag, program.grade_level, program.code)
        changes = {key: value for key, value in (payload.get('changes') or {}).items() if key in self.FIELDS}
        if not changes:
            raise ValidationError({'detail': 'There is nothing to change.'})
        serializer = AdminProgramSerializer(program, data=changes, partial=True)
        serializer.is_valid(raise_exception=True)
        current = AdminProgramSerializer(program).data
        before = _snapshot(payload, lambda: {key: current[key] for key in changes})
        return {'program': program.id, 'changes': changes, 'before': before}

    def describe(self, cleaned):
        program = Program.objects.get(pk=cleaned['program'])
        return short(f'Edit {program.code}: {", ".join(humanize(key) for key in cleaned["changes"])}')

    def diff(self, cleaned):
        rows = []
        for key, after in cleaned['changes'].items():
            before = cleaned['before'].get(key)
            if key == 'subjects':
                before, after = _subjects_text(before or []), _subjects_text(after)
            rows.append(change(humanize(key), before, after))
        return rows

    def execute(self, cleaned, owner):
        program = Program.objects.get(pk=cleaned['program'])
        update_program(program, cleaned['changes'], owner)
        return {'program': program.code}


class EditWebsitePages(Activity):
    key = 'edit_website_pages'
    label = 'Edit website pages'
    description = 'Propose changes to the Landing, About, Contact or Footer page of the public website.'
    owner_role = ADMIN
    holder_roles = (HEAD_TEACHER, TEACHER)
    work_slug = 'website'
    scope_label = 'Pages'
    scope_all = 'All pages'

    def scope_options(self, owner):
        return [{'value': value, 'label': label} for value, label in PAGES.items()]

    def scope_text(self, scope):
        return PAGES.get(scope, scope) if scope else self.scope_all

    def clean(self, payload, tag, proposer):
        document = payload.get('document')
        if document not in PAGES:
            raise ValidationError({'detail': 'Choose a website page.'})
        if tag.scope and tag.scope != document:
            raise ValidationError({'detail': 'That page is outside the pages this tag covers.'})
        changes = payload.get('changes')
        if not isinstance(changes, dict) or not changes:
            raise ValidationError({'detail': 'There is nothing to change.'})
        if len(json.dumps(changes)) > MAX_PAGE_CHANGE:
            raise ValidationError({'detail': 'These changes are too large for one request.'})
        require_safe_links(changes)
        live = live_document(document)
        before = _snapshot(payload, lambda: {key: live.get(key) for key in changes})
        return {'document': document, 'changes': changes, 'before': before}

    def describe(self, cleaned):
        fields = ', '.join(humanize(key) for key in cleaned['changes'])
        return short(f'Edit the {PAGES[cleaned["document"]]} page: {fields}')

    def diff(self, cleaned):
        return field_changes(cleaned['before'], cleaned['changes'])

    def execute(self, cleaned, owner):
        live = live_document(cleaned['document'])
        changed = _changed_since(cleaned['before'], live, cleaned['changes'])
        if changed:
            raise ActivityFailed(
                f'{", ".join(changed)} changed on the live page after this was prepared. Prepare it again.'
            )
        save_document(cleaned['document'], {**live, **cleaned['changes']}, owner)
        return {'page': PAGES[cleaned['document']]}

    def discard(self, payload):
        delete_unused_uploads(upload_urls(payload.get('changes')) - upload_urls(payload.get('before')))


class PostNews(Activity):
    key = 'post_news'
    label = 'Post news & events'
    description = 'Propose new posts, changes, publishing or deleting on the News & Events page.'
    owner_role = ADMIN
    holder_roles = (HEAD_TEACHER, TEACHER)
    work_slug = 'news'
    scope_label = ''
    scope_all = 'All posts'
    FIELDS = ('title', 'body', 'image', 'category', 'kind', 'event_date', 'event_end_date', 'location', 'is_published')

    def scope_options(self, owner):
        return []

    def _post(self, payload):
        row = Announcement.objects.filter(pk=payload.get('announcement')).first()
        if row is None:
            raise ValidationError({'detail': 'That post no longer exists.'})
        return row

    def clean(self, payload, tag, proposer):
        action = payload.get('action')
        fields = {key: value for key, value in (payload.get('fields') or {}).items() if key in self.FIELDS}
        if action == 'create':
            AnnouncementSerializer(data=fields).is_valid(raise_exception=True)
            return {'action': action, 'fields': fields}
        if action not in ('update', 'delete'):
            raise ValidationError({'detail': 'Choose to create, update or delete a post.'})
        row = self._post(payload)
        current = AnnouncementSerializer(row).data
        if action == 'delete':
            before = _snapshot(payload, lambda: {key: current[key] for key in ('title', 'kind', 'is_published')})
            return {'action': action, 'announcement': row.id, 'before': before}
        if not fields:
            raise ValidationError({'detail': 'There is nothing to change.'})
        AnnouncementSerializer(row, data=fields, partial=True).is_valid(raise_exception=True)
        before = _snapshot(payload, lambda: {key: current[key] for key in fields})
        return {'action': action, 'announcement': row.id, 'fields': fields, 'before': before}

    def describe(self, cleaned):
        if cleaned['action'] == 'create':
            state = 'published' if cleaned['fields'].get('is_published') else 'as a draft'
            return short(f'Post "{cleaned["fields"].get("title", "")}" ({state})')
        title = cleaned['before'].get('title') or Announcement.objects.get(pk=cleaned['announcement']).title
        if cleaned['action'] == 'delete':
            return short(f'Delete "{title}"')
        return short(f'Update "{title}": {", ".join(humanize(key) for key in cleaned["fields"])}')

    def diff(self, cleaned):
        if cleaned['action'] == 'delete':
            return [change('Post', cleaned['before'].get('title'), 'Deleted')]
        before = cleaned.get('before') or {}
        return [change(humanize(key), before.get(key), value) for key, value in cleaned['fields'].items()]

    def execute(self, cleaned, owner):
        if cleaned['action'] == 'create':
            serializer = AnnouncementSerializer(data=cleaned['fields'])
            serializer.is_valid(raise_exception=True)
            return {'announcement': save_new_announcement(serializer, owner).id}
        row = Announcement.objects.filter(pk=cleaned['announcement']).first()
        if row is None:
            raise ActivityFailed('That post was already deleted.')
        if cleaned['action'] == 'delete':
            image = row.image
            row.delete()
            delete_unused_uploads({image} if image else set())
            return {'deleted': cleaned['before'].get('title')}
        changed = _changed_since(cleaned['before'], AnnouncementSerializer(row).data, cleaned['fields'])
        if changed:
            raise ActivityFailed(f'{", ".join(changed)} changed after this was prepared. Prepare it again.')
        serializer = AnnouncementSerializer(row, data=cleaned['fields'], partial=True)
        serializer.is_valid(raise_exception=True)
        save_announcement_changes(serializer)
        return {'announcement': row.id}

    def discard(self, payload):
        delete_unused_uploads(upload_urls(payload.get('fields')) - upload_urls(payload.get('before')))


class RateProgramProfiles(Activity):
    """Expert validation of college program profiles. Ratings are inputs; the Admin later applies the median."""

    key = 'rate_programs'
    label = 'Rate college program profiles'
    description = (
        'Rate how important each skill area is for a college program, relative to a typical Grade 12 graduate. '
        'The Admin applies the median of several experts as the validated profile.'
    )
    owner_role = ADMIN
    holder_roles = (HEAD_TEACHER, TEACHER)
    work_slug = 'program-ratings'

    def scope_options(self, owner):
        return []

    def clean(self, payload, tag, proposer):
        program = CollegeProgram.objects.filter(code=str(payload.get('program') or '')).first()
        if program is None:
            raise ValidationError({'detail': 'Choose a college program.'})
        round_number = payload.get('round') if isinstance(payload.get('round'), int) else rating_round(program)
        ratings = clean_ratings(payload.get('ratings'))
        if _stored_fingerprint(program, proposer, round_number) == _rating_fingerprint(ratings):
            raise ValidationError(
                {'detail': 'These ratings were already recorded. Change the relative importance if experts still disagree.'}
            )
        return {
            'program': program.code,
            'round': round_number,
            'rater': proposer.pk,
            'ratings': ratings,
        }

    def describe(self, cleaned):
        program = CollegeProgram.objects.filter(code=cleaned['program']).first()
        name = program.name if program else cleaned['program']
        count = len(cleaned['ratings'])
        return short(f'Rate {name}: {count} skill area{"s" if count != 1 else ""}')

    def diff(self, cleaned):
        rows = []
        for row in cleaned['ratings']:
            after = IMPORTANCE_LABELS.get(row.get('importance'), row['level'])
            rows.append(change(humanize(row['domain']), None, after))
        return rows

    def execute(self, cleaned, owner):
        program = CollegeProgram.objects.filter(code=cleaned['program']).first()
        if program is None:
            raise ActivityFailed('This college program no longer exists.')
        if rating_round(program) != cleaned['round']:
            raise ActivityFailed('The profile was validated again after these ratings were prepared. Rate it again.')
        rater = User.objects.filter(pk=cleaned['rater']).first()
        if rater is None:
            raise ActivityFailed('The rater no longer has an account.')
        save_ratings(program, rater, cleaned['ratings'])
        return {'program': program.code, 'round': cleaned['round']}

