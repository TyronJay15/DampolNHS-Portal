"""The chatbot's message flow, in order. The view rejects empty and over-long messages and removes personal
details (apps.chatbot.privacy) first. Nothing here trusts the message, and nothing here can reach records beyond
the FAQs, the program list and the live topics.

  1. moderation (apps.chatbot.moderation): prompt injection and secret requests are refused, safety reports and
     self-harm get the school's help routes, abuse gets the respectful-language reminder
  2. greetings and thanks
  3. intent and relevance (apps.chatbot.relevance): answer, clarify, not verified, or out of scope
  4. the verified answer: live data, Gemini phrasing of the FAQ notes, or the FAQ itself
"""

from dataclasses import dataclass, field

from apps.chatbot import moderation, responses
from apps.chatbot.live_data import is_live, live_answer
from apps.chatbot.models import FaqEntry
from apps.chatbot.relevance import decide, small_talk
from apps.ml.gemini import phrase_answer
from apps.ml.intent import answers_for, best_faq_entry, corrected, matching_faq_answer, school_pack

# Shown when a question is too vague to point at a topic.
GENERAL_OPTIONS_TOPICS = ('registration', 'approval', 'programs', 'grades', 'login', 'contact')


@dataclass(frozen=True)
class Reply:
    answer: str
    kind: str
    topic: str
    confidence: float = 0.0
    source: str = 'fallback'
    options: tuple = field(default_factory=tuple)
    keep_text: bool = True  # False: the question is stored without its text (abuse, attacks, personal reports)


MODERATED = {
    'injection': Reply(responses.REFUSED, 'refused', 'refused', source='moderation', keep_text=False),
    'abuse': Reply(responses.RESPECTFUL_LANGUAGE, 'moderated', 'moderated', source='moderation', keep_text=False),
    'self_harm': Reply(responses.SELF_HARM, 'safety', 'safety', source='safety', keep_text=False),
}


def respond(question, user):
    """The reply to one question that already passed the view's checks and redaction."""
    verdict = moderation.check(question)
    if verdict in MODERATED:
        return MODERATED[verdict]
    if verdict == 'safety':
        return _safety()

    talk, filipino = small_talk(question)
    if talk == 'greeting':
        text = responses.GREETING_FILIPINO if filipino else responses.GREETING
        return Reply(text, 'greeting', 'small_talk', 1.0, 'rule')
    if talk == 'thanks':
        text = responses.THANKS_FILIPINO if filipino else responses.THANKS
        return Reply(text, 'thanks', 'small_talk', 1.0, 'rule')

    decision = decide(question)
    if decision.kind == 'out_of_scope':
        return Reply(responses.OUT_OF_SCOPE, 'out_of_scope', 'out_of_scope', decision.confidence, 'relevance')
    if decision.kind == 'not_verified':
        return Reply(responses.NOT_VERIFIED, 'not_verified', 'other', decision.confidence, 'relevance')
    if decision.kind == 'clarify':
        return _clarify(question, decision)
    return _answer(question, decision, user)


def _safety():
    entry = FaqEntry.objects.filter(is_active=True, topic__iexact='safety').order_by('sort_order', 'pk').first()
    return Reply(entry.answer if entry else responses.SAFETY, 'safety', 'safety', 1.0, 'safety', keep_text=False)


def _answer(question, decision, user):
    topic = decision.topic
    if topic == 'safety':
        return _safety()
    if is_live(topic):
        # Today's numbers come from the database and Django writes the sentence; Gemini never sees them.
        answer, source = live_answer(topic, user)
        return Reply(answer, 'answer', topic, decision.confidence, source)

    answers = answers_for(topic)
    if not answers:
        return Reply(responses.NOT_VERIFIED, 'not_verified', topic, decision.confidence, 'relevance')
    faq = matching_faq_answer(corrected(question), topic) or answers[0]
    written = phrase_answer(question, topic, school_pack(topic))
    # Gemini only rewords the notes; anything it writes that moderation would stop is replaced by the FAQ itself.
    if written and moderation.check(written) is None:
        return Reply(written, 'answer', topic, decision.confidence, 'gemini')
    return Reply(faq, 'answer', topic, decision.confidence, 'faq')


def _topic_question(topic, question=''):
    """The FAQ question that stands for a topic: the one closest to the visitor's words, else the first."""
    entry = best_faq_entry(corrected(question), topic) if question else None
    entry = entry or FaqEntry.objects.filter(is_active=True, topic__iexact=topic).order_by('sort_order', 'pk').first()
    return entry.question if entry else None


def _clarify(question, decision):
    if decision.candidates:
        options = [_topic_question(topic, question) for topic in decision.candidates]
        text = responses.CLARIFY
    else:
        options = [_topic_question(topic) for topic in GENERAL_OPTIONS_TOPICS]
        text = responses.CLARIFY_GENERAL
    options = tuple(dict.fromkeys(option for option in options if option))
    if not options:
        return Reply(responses.NOT_VERIFIED, 'not_verified', decision.topic, decision.confidence, 'relevance')
    return Reply(text, 'clarify', decision.topic, decision.confidence, 'clarify', options)
