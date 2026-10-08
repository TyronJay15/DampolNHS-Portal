"""Chatbot answers that need today's numbers from the school's own records.

Each live topic names who may ask it (PUBLIC, or a set of roles), a function that reads the database, and a function
that writes the sentence. Django writes every sentence itself: the numbers are never sent to Gemini, which could
round or change them. Handlers return aggregate counts only, never a list of students or any personal detail.

A topic is PUBLIC only when its answer is a school-wide aggregate that is fine for any visitor to read (the current
enrollment total). Anything more sensitive gets its own roles, checked on the server for each question.

To add a topic: write a summary function and a sentence function, register them in LIVE_TOPICS, add the topic's
FAQ row (apps.chatbot.seeds) and paraphrases (apps.ml.intent.PARAPHRASES), then retrain the classifier
(`python manage.py seed_chatbot_faqs`).
"""

import logging
from dataclasses import dataclass
from typing import Callable

from django.db import DatabaseError

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import User
from apps.people.models import Registration, StudentSection
from apps.school.models import SchoolYear

logger = logging.getLogger(__name__)

NO_SCHOOL_YEAR = 'There is no active school year configured yet, so there is no current enrollment total.'
UNAVAILABLE = 'That information cannot be loaded right now. Please try again later.'

# ChatQuestion.source values for answers from this module.
SOURCE_LIVE = 'live_data'
SOURCE_DENIED = 'live_denied'
SOURCE_ERROR = 'live_error'


def current_school_year():
    """The active school year: marked current and not archived. None when the school has not set one."""
    return SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()


def _visible_students():
    """Student accounts that are not archived, removed or suspended."""
    return User.objects.filter(role=User.Role.STUDENT).exclude(account_status__in=HIDDEN)


def registered_this_year(year):
    """Metric: students whose approved registration belongs to this school year (new enrollees, mostly Grade 11)."""
    approved = Registration.objects.filter(school_year=year, status=Registration.Status.APPROVED)
    return _visible_students().filter(pk__in=approved.values('user_id'))


def placed_this_year(year):
    """Metric: students with an active section placement this school year, including returning Grade 12 students
    whose only registration is from an earlier year (a registration is one per student and is never moved)."""
    placements = StudentSection.objects.filter(school_year=year, is_active=True)
    return _visible_students().filter(pk__in=placements.values('student__user_id'))


def current_enrollment_summary():
    """The current student body: everyone placed in a section this school year, plus everyone approved for this
    school year who is not placed yet. Each student counts once, and archived, removed or suspended accounts never
    count. Read-only: three COUNT queries, no rows are loaded."""
    year = current_school_year()
    if year is None:
        return {'available': False, 'message': NO_SCHOOL_YEAR}
    registered = registered_this_year(year)
    placed = placed_this_year(year)
    return {
        'available': True,
        'school_year': year.label,
        'total': (registered | placed).distinct().count(),
        # Kept for future questions ("how many are already in sections?"); the enrollment answer uses the total.
        'registered_this_year': registered.count(),
        'placed_in_sections': placed.count(),
    }


def enrollment_sentence(summary):
    if not summary['available']:
        return summary['message']
    total = summary['total']
    if total == 1:
        return f'There is currently 1 enrolled student for School Year {summary["school_year"]}.'
    return f'There are currently {total} enrolled students for School Year {summary["school_year"]}.'


PUBLIC = None  # LiveTopic.roles for an answer anyone may receive, signed in or not


@dataclass(frozen=True)
class LiveTopic:
    roles: frozenset | None  # PUBLIC, or the User.Role values allowed to receive the answer
    summary: Callable[[], dict]  # reads the database; returns aggregate data only
    sentence: Callable[[dict], str]  # turns the data into the reply
    refused: str = ''  # for role-limited topics: the reply for everyone else, revealing nothing about the data


LIVE_TOPICS = {
    # Public: the landing-page chatbot answers any visitor with the school-wide total and the school year only.
    'enrollment_stats': LiveTopic(
        roles=PUBLIC,
        summary=current_enrollment_summary,
        sentence=enrollment_sentence,
    ),
}


def is_live(topic):
    return topic in LIVE_TOPICS


def may_ask(user, topic):
    """Public topics: anyone. Role-limited topics: decided on the server from the signed-in account, never from
    anything the browser sends."""
    roles = LIVE_TOPICS[topic].roles
    if roles is PUBLIC:
        return True
    return bool(
        user
        and user.is_authenticated
        and getattr(user, 'can_sign_in', False)
        and getattr(user, 'role', None) in roles
    )


def live_answer(topic, user):
    """(reply, source) for a live topic. A role-limited topic refuses without revealing the data; a database failure
    is logged and answered plainly, never with a made-up number."""
    live = LIVE_TOPICS[topic]
    if not may_ask(user, topic):
        return live.refused, SOURCE_DENIED
    try:
        summary = live.summary()
    except DatabaseError:
        logger.exception('Live chatbot topic %s could not be read.', topic)
        return UNAVAILABLE, SOURCE_ERROR
    return live.sentence(summary), SOURCE_LIVE
