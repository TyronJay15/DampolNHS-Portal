"""Layers 2 and 3 of the chatbot: what the visitor wants, and whether a verified answer fits well enough.

decide(question) returns a Decision with one of these kinds:

  answer        a school topic, either with high confidence and a clear lead over the next topic, or with
                moderate confidence and a close match to one of that topic's approved FAQs
  clarify       a school topic that the question touches, but with lower confidence or two topics close
                together: the visitor picks one of the approved questions offered
  not_verified  about the school, but no verified answer fits (Scenario H)
  out_of_scope  not about Dampol NHS or the portal (sports, gossip, trivia, homework, shopping...)

The thresholds below were chosen with `python manage.py evaluate_chatbot --sweep`, which tries every combination
over a labeled set of questions (apps.chatbot.evaluation) and ranks them by fewest wrong answers, then accuracy.
Re-run it after changing FAQs or phrasings, and keep these values only while it still agrees.
"""

import re
from dataclasses import dataclass, field

from apps.chatbot.moderation import plain
from apps.ml.intent import FAQ_STOP_WORDS, corrected, faq_match, known_words, rank_topics

ANSWER_MIN = 0.4  # the best school topic's probability needed to answer it
CLARIFY_MIN = 0.3  # below this, no school topic is a candidate at all
MARGIN = 0.2  # the lead the best school topic needs over the second to be answered without asking
OUT_OF_SCOPE_MIN = 0.35  # the out-of-scope class's probability that declines the question outright
FAQ_MIN_WORDS = 2  # words the question must share with one approved FAQ of the best topic ...
FAQ_MIN_SHARE = 0.4  # ... and the share of the question's words they make up, to answer below ANSWER_MIN

OUT_OF_SCOPE_TOPIC = 'out_of_scope'

# Words that place a question at the school even when no FAQ answers it ("Is there a uniform policy?").
SCHOOL_WORDS = frozenset(
    'dampol nhs school paaralan eskwela eskwelahan campus teacher teachers guro adviser principal registrar guidance '
    'counselor class classes classmate classmates kaklase klase section subject subjects enrollment enroll enrolled '
    'grade grades report card lrn portal account uniform tuition fee fees schedule exam exams quarter semester shs '
    'strand strands deped library canteen clinic scholarship graduation pta student students estudyante learner learners office faculty admission '
    'requirements form id help tulong register registration login password approval approved pending program '
    'programs event events announcement announcements contact'.split()
)
# Words too common to carry a question by themselves: "school?" or "portal" alone is asked about, not answered.
GENERIC = frozenset('dampol nhs school paaralan student students portal help question ask know tell please'.split())

GREETINGS = re.compile(
    r'^(hi|hello|helo|hey|hiya|good (morning|afternoon|evening|day)|greetings|'
    r'(magandang )?(umaga|hapon|gabi|araw)|kumusta|kamusta|musta)( po| there| bot| assistant| everyone)?$'
)
THANKS = re.compile(
    r'^(ok(ay)? )?(thank you|thanks|thank u|thanks a lot|ty|salamat|maraming salamat|bye|goodbye|paalam)'
    r'( po| so much| very much| ulit)?$'
)
FILIPINO_SMALL_TALK = re.compile(r'\b(magandang|umaga|hapon|gabi|araw|kumusta|kamusta|musta|salamat|paalam|po)\b')


@dataclass(frozen=True)
class Decision:
    kind: str
    topic: str
    confidence: float = 0.0
    candidates: tuple = field(default_factory=tuple)  # topics to offer when kind == 'clarify'


def small_talk(question):
    """'greeting', 'thanks' or None, and whether it was said in Filipino. Only whole messages count:
    "hi, how do I register?" is a question, not a greeting."""
    text = plain(question).replace("'", '')
    for kind, pattern in (('greeting', GREETINGS), ('thanks', THANKS)):
        if pattern.match(text):
            return kind, bool(FILIPINO_SMALL_TALK.search(text))
    return None, False


@dataclass(frozen=True)
class Signals:
    """What the classifier says about one message, computed once so thresholds can be applied many times."""

    ranked: tuple  # (topic, probability), best first; empty when no model is trained
    specific: bool  # has a known word beyond the generic ones ("school", "portal")
    related: bool  # mentions the school or a school matter
    faq_words: int = 0  # words shared with the closest approved FAQ of the best school topic
    faq_share: float = 0.0  # the share of the question's words that those make up


def signals(question):
    known = known_words(question)
    words = set(re.findall(r'[a-z]+', plain(question))) | known
    ranked = tuple(rank_topics(question))
    school = [topic for topic, _score in ranked if topic != OUT_OF_SCOPE_TOPIC]
    # Generic words do not count as a match: "school" appears in many FAQs and says nothing about which one.
    specific_text = ' '.join(word for word in corrected(question).split() if word not in GENERIC)
    _entry, faq_words, faq_share = faq_match(specific_text, school[0]) if school else (None, 0, 0.0)
    return Signals(
        ranked=ranked,
        specific=bool(known - GENERIC - FAQ_STOP_WORDS),
        related=bool(words & SCHOOL_WORDS),
        faq_words=faq_words,
        faq_share=faq_share,
    )


def decide(question):
    """The relevance decision for a message that passed moderation and is not small talk."""
    return decide_from(signals(question))


def decide_from(
    found,
    *,
    answer_min=ANSWER_MIN,
    clarify_min=CLARIFY_MIN,
    margin=MARGIN,
    out_min=OUT_OF_SCOPE_MIN,
    faq_min_words=FAQ_MIN_WORDS,
    faq_min_share=FAQ_MIN_SHARE,
):
    """Apply the thresholds to the signals. The keyword arguments exist for the sweep in apps.chatbot.evaluation."""
    if not found.ranked:
        return Decision('not_verified' if found.related else 'out_of_scope', 'other')

    out_score = dict(found.ranked).get(OUT_OF_SCOPE_TOPIC, 0.0)
    school = [(topic, score) for topic, score in found.ranked if topic != OUT_OF_SCOPE_TOPIC]
    best, best_score = school[0] if school else ('other', 0.0)
    second_score = school[1][1] if len(school) > 1 else 0.0

    if out_score >= out_min and out_score > best_score:
        return Decision('out_of_scope', OUT_OF_SCOPE_TOPIC, out_score)
    # Only generic words ("school", "portal"): nothing specific enough to answer, so the visitor is asked.
    if not found.specific:
        if found.related:
            return Decision('clarify', 'other', best_score)
        return Decision('out_of_scope', 'other', out_score)
    confident = best_score >= answer_min and best_score - second_score >= margin
    matched = best_score >= clarify_min and found.faq_words >= faq_min_words and found.faq_share >= faq_min_share
    if confident or matched:
        return Decision('answer', best, best_score)
    # Asking "did you mean" only makes sense when the question touches one of the topic's FAQs at all.
    if best_score >= clarify_min and found.faq_words >= 1:
        close = tuple(topic for topic, score in school[:2] if score >= clarify_min / 2)
        return Decision('clarify', best, best_score, close)
    if found.related:
        return Decision('not_verified', 'other', best_score)
    return Decision('out_of_scope', 'other', best_score)
