"""A labeled set of questions for choosing and checking the relevance thresholds (apps.chatbot.relevance).

Each case is (question, accepted outcomes, group). An outcome is 'answer:<topic>', 'clarify', 'not_verified' or
'out_of_scope'. Group 'heldout' wordings do not appear in the training phrasings, so they measure how the
classifier generalizes; group 'spec' are the project's required examples, kept as regression checks.

Only messages that reach the relevance layer belong here: moderation and small talk are rule-based and have
their own tests.
"""

from itertools import product

from apps.chatbot.relevance import (
    ANSWER_MIN,
    CLARIFY_MIN,
    FAQ_MIN_SHARE,
    FAQ_MIN_WORDS,
    MARGIN,
    OUT_OF_SCOPE_MIN,
    decide_from,
    signals,
)

STATUS = ('answer:approval', 'answer:registration')

CASES = (
    # Registration and enrollment
    ('how do I sign up for the portal', ('answer:registration',), 'heldout'),
    ('paano gumawa ng account bilang estudyante', ('answer:registration',), 'heldout'),
    ('what do I need to fill out to register', ('answer:registration',), 'heldout'),
    ('I want to enroll for next school year', ('answer:registration',), 'heldout'),
    ('how to enroll in grade 11', ('answer:registration',), 'heldout'),
    ('mag eenroll po ako paano', ('answer:registration',), 'heldout'),
    ('can I edit my registration details', ('answer:registration',), 'heldout'),
    ('Paano ako mag-enroll?', ('answer:registration',), 'spec'),
    ('Paano mag-register?', ('answer:registration',), 'spec'),
    # Approval and enrollment status
    ('my account still says pending', ('answer:approval',), 'heldout'),
    ('how long before the admin approves my registration', ('answer:approval',), 'heldout'),
    ('na reject ako ano gagawin ko', ('answer:approval',), 'heldout'),
    ('is my registration approved already', STATUS, 'heldout'),
    ('how do i chek my enrolment staus', STATUS, 'heldout'),
    ('Bakit pending yung account ko?', ('answer:approval',), 'spec'),
    ('How can I check my enrollment status?', STATUS, 'spec'),
    ('Paano ko malalaman kung approved na ang enrollment ko?', STATUS, 'spec'),
    ('Saan makikita enrollment status?', STATUS, 'spec'),
    # Programs
    ('what strands can I choose', ('answer:programs',), 'heldout'),
    ('is STEM offered this year', ('answer:programs',), 'heldout'),
    ('anong programs meron sa senior high', ('answer:programs',), 'heldout'),
    ('subjects of the ICT strand', ('answer:programs',), 'heldout'),
    ('What programs are available?', ('answer:programs',), 'spec'),
    ('Ano ang available na SHS programs?', ('answer:programs',), 'spec'),
    # Login and passwords
    ('lost my password what do I do', ('answer:login',), 'heldout'),
    ('how do I log into my student account', ('answer:login',), 'heldout'),
    ('di ako maka login', ('answer:login',), 'heldout'),
    ('what username do teachers use', ('answer:login',), 'heldout'),
    ('the reset code never arrived', ('answer:login',), 'heldout'),
    ('How do I reset my password?', ('answer:login',), 'spec'),
    # Grades
    ('when will our report cards be released', ('answer:grades',), 'heldout'),
    ('my grade in math looks wrong', ('answer:grades',), 'heldout'),
    ('where do I view my report card', ('answer:grades',), 'heldout'),
    ('kailan makikita ang grades', ('answer:grades',), 'heldout'),
    ('Saan ko makikita yung grades ko sa portal?', ('answer:grades',), 'spec'),
    ('Saan ko makita grades ko?', ('answer:grades',), 'spec'),
    ('Pwede ko bang makita grades ko?', ('answer:grades',), 'spec'),
    # Contact, events, live enrollment numbers
    ("what is the school's phone number", ('answer:contact',), 'heldout'),
    ('where is dampol nhs located', ('answer:contact',), 'heldout'),
    ('how do I message the school office', ('answer:contact',), 'heldout'),
    ('any events next week', ('answer:events',), 'heldout'),
    ('where are the school announcements', ('answer:events',), 'heldout'),
    ('may activity ba bukas', ('answer:events',), 'heldout'),
    ('how many learners are enrolled now', ('answer:enrollment_stats',), 'heldout'),
    ('ilan ang students ng dampol ngayon', ('answer:enrollment_stats',), 'heldout'),
    # Gentle safety wordings that moderation does not catch
    ('who can I talk to if my classmates make fun of me', ('answer:safety',), 'heldout'),
    ('sino ang pwede kong kausapin sa guidance', ('answer:safety',), 'heldout'),
    # About the school, but no verified answer exists
    ('Is there a school uniform policy?', ('not_verified',), 'spec'),
    ('does the school have a library', ('not_verified',), 'heldout'),
    ('who is the principal of dampol nhs', ('not_verified',), 'heldout'),
    ('can I transfer to another section', ('not_verified',), 'heldout'),
    ('what time do classes start', ('not_verified',), 'heldout'),
    ('when is the graduation ceremony', ('not_verified', 'answer:events'), 'heldout'),
    # Too vague to answer
    ('school', ('clarify',), 'heldout'),
    ('portal', ('clarify',), 'heldout'),
    ('help', ('clarify',), 'heldout'),
    # Not about the school
    ('Who won the NBA championship?', ('out_of_scope',), 'spec'),
    ("who is kathryn bernardo's boyfriend", ('out_of_scope',), 'heldout'),
    ('what is the capital of japan', ('out_of_scope',), 'heldout'),
    ('write my essay about global warming', ('out_of_scope',), 'heldout'),
    ('best phone under 10k', ('out_of_scope',), 'heldout'),
    ('who will win the next election', ('out_of_scope',), 'heldout'),
    ('how to cook sinigang', ('out_of_scope',), 'heldout'),
    ('solve 2x + 5 = 11', ('out_of_scope',), 'heldout'),
    ("what's the latest kpop news", ('out_of_scope',), 'heldout'),
    ('recommend a good netflix series', ('out_of_scope',), 'heldout'),
    ('how do I court a girl', ('out_of_scope',), 'heldout'),
    ('tell me something funny', ('out_of_scope',), 'heldout'),
    ('what is the bitcoin price today', ('out_of_scope',), 'heldout'),
    ('best laptop to buy for students', ('out_of_scope',), 'heldout'),
    ('who is the best basketball player of all time', ('out_of_scope',), 'heldout'),
    ('translate good morning to spanish', ('out_of_scope',), 'heldout'),
)

GRID = {
    'answer_min': (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55),
    'clarify_min': (0.1, 0.15, 0.2, 0.25, 0.3),
    'margin': (0.0, 0.05, 0.1, 0.15, 0.2),
    'out_min': (0.2, 0.25, 0.3, 0.35, 0.4, 0.5),
    'faq_min_words': (2, 3),
    'faq_min_share': (0.3, 0.4, 0.5, 0.6, 0.7),
}
DEFAULTS = {
    'answer_min': ANSWER_MIN,
    'clarify_min': CLARIFY_MIN,
    'margin': MARGIN,
    'out_min': OUT_OF_SCOPE_MIN,
    'faq_min_words': FAQ_MIN_WORDS,
    'faq_min_share': FAQ_MIN_SHARE,
}


def outcome(decision):
    return f'answer:{decision.topic}' if decision.kind == 'answer' else decision.kind


def evaluate(found=None, **thresholds):
    """Accuracy per group, the number of wrong answers, and the failed cases, for one set of thresholds (the
    defaults when none are given). A wrong answer is an answer where a different outcome was expected: worse than
    asking the visitor to clarify, because it states something that does not fit the question."""
    found = found or [signals(question) for question, _accepted, _group in CASES]
    thresholds = {**DEFAULTS, **thresholds}
    totals, failures, wrong_answers = {}, [], 0
    for (question, accepted, group), facts in zip(CASES, found):
        got = outcome(decide_from(facts, **thresholds))
        right, count = totals.get(group, (0, 0))
        totals[group] = (right + (got in accepted), count + 1)
        if got not in accepted:
            failures.append((question, accepted, got))
            wrong_answers += got.startswith('answer:')
    right = sum(r for r, _c in totals.values())
    count = sum(c for _r, c in totals.values())
    return {
        'accuracy': right / count,
        'wrong_answers': wrong_answers,
        'groups': {group: r / c for group, (r, c) in totals.items()},
        'failures': failures,
    }


def sweep():
    """Every threshold combination of GRID, best first: fewest wrong answers, then highest accuracy, then the
    stricter answer threshold, margin and FAQ share, so the assistant answers only when it is surer."""
    found = [signals(question) for question, _accepted, _group in CASES]
    rows = []
    for values in product(*GRID.values()):
        thresholds = dict(zip(GRID, values))
        result = evaluate(found, **thresholds)
        rows.append((result['wrong_answers'], result['accuracy'], thresholds))
    rows.sort(
        key=lambda row: (-row[0], row[1], row[2]['answer_min'], row[2]['margin'], row[2]['faq_min_share']),
        reverse=True,
    )
    return rows
