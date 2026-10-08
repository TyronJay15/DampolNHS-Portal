import hashlib

from apps.chatbot.models import FaqEntry
from apps.ml.store import last_artifact, save_run
from apps.ml.text import MultinomialNB, TfidfVectorizer, tokenize
from apps.school.curriculum import GRADE_LEVELS, curriculum_for, programs_for
from apps.school.models import SchoolYear

MIN_CONFIDENCE = 0.42
# Seed phrasings that widen each FAQ topic. Topics themselves come from FaqEntry rows.
PARAPHRASES = {
    'registration': (
        'how to sign up',
        'create a student account',
        'where do i enroll',
        'start my registration',
        'i want to apply',
        'how do i enroll in dampol nhs',
        'paano mag enroll',
        'paano mag register ng student account',
        'gusto kong mag apply sa school',
        'what do i need for student registration',
        'i submitted my registration what now',
        'mali ang nailagay ko sa registration',
        'where can i check my application status',
    ),
    'programs': (
        'what strands are offered',
        'difference between stem and stemc',
        'grade 11 clusters',
        'is there ict',
        'list of shs programs',
        'what programs are available this school year',
        'where can i see the subjects for a strand',
        'paano pumili ng shs program',
        'anong strand ang inooffer ng school',
        'available ba ang program na ito',
        'show me the senior high programs',
        'saan makikita ang subjects ng program',
        'what are the current school offerings',
    ),
    'login': (
        'cannot sign in',
        'forgot my lrn login',
        'teacher email login',
        'how to enter the portal',
        'sign in page',
        'how do students log in',
        'how do teachers sign in',
        'how can i reset my password',
        'i forgot my password',
        'paano mag login sa portal',
        'nakalimutan ko ang password ko',
        'hindi ako makapasok sa account',
        'i did not receive the reset code',
    ),
    'approval': (
        'why am i still pending',
        'when will admin approve me',
        'my registration is waiting',
        'account not approved yet',
        'rejected application',
        'how long does account review take',
        'why is student approval pending',
        'my application needs admin review',
        'bakit hindi pa naaapprove ang account',
        'sino ang nag aapprove ng registration',
        'what do i do after rejection',
        'check my student application status',
        'my account is waiting for approval',
        'admin has not approved my account',
        'my student account was rejected',
        'how long does school approval take',
        'bakit pending ang account ko',
        'hindi pa approved ang registration ko',
        'nareject ang application ko',
        'who reviews student registrations',
    ),
    'grades': (
        'when will i see my report card',
        'are grades released',
        'who approves grades',
        'i cannot see my scores',
        'adviser show card',
        'why is my report card hidden',
        'a subject grade is missing',
        'how do i report an incorrect score',
        'kailan lalabas ang grades ko',
        'bakit hindi ko makita ang report card',
        'sino ang nag aapprove ng grades',
        'one of my subjects has no grade',
        'my report card is still locked',
    ),
    'contact': (
        'school phone number',
        'facebook page of the school',
        'where is the campus',
        'email the registrar',
        'how to reach dampol nhs',
        'where is the school contact page',
        'what is the school address',
        'where can i find official school links',
        'paano kontakin ang paaralan',
        'saan makikita ang address ng school',
        'school office contact details',
        'where can i check office hours',
        'official facebook link please',
    ),
    'events': (
        'upcoming school events',
        'is there an activity this week',
        'dashboard events',
        'campus calendar',
        'when is the next event',
        'where can i read school announcements',
        'did the school event schedule change',
        'where do i find activity dates',
        'ano ang susunod na school event',
        'saan makikita ang announcements',
        'is the activity postponed',
        'latest school news and notices',
        'where can parents see upcoming activities',
    ),
    # Answered from live data (apps.chatbot.live_data); never with a stored number.
    # English and Filipino are mixed, because the last fifth of each topic is held out to measure accuracy.
    'enrollment_stats': (
        'how many students are currently enrolled',
        'ilang estudyante ang kasalukuyang enrolled',
        'how many students are enrolled',
        'ilan ang enrolled students',
        'current enrolled students',
        'ilan ang students ngayon',
        'current student population',
        'ilang estudyante ang enrolled',
        'what is the current student population',
        'number of enrolled students',
        'total enrolled students',
        'how many students this school year',
        'total students this school year',
        'enrollment count this year',
    ),
}

FAQ_STOP_WORDS = frozenset(
    'a an and are ba can do does for from how i in is it ko mga ng of on or sa the to what when '
    'where which who why with you your my ang ano paano po pa ba'.split()
)

FALLBACK = (
    'I can help with registration, programs, login, account approval, grades, events, and contact information.'
)
EVENT_ANSWER = (
    'Upcoming events appear on the dashboards after you sign in. Public news stays on the Announcements page.'
)


def _rows():
    rows = []
    for entry in FaqEntry.objects.filter(is_active=True):
        topic = entry.topic.strip().lower()
        if not topic:
            continue
        rows.append((entry.question, topic))
        for keyword in entry.keyword_list():
            rows.append((keyword, topic))
    for topic, phrases in PARAPHRASES.items():
        rows.extend((phrase, topic) for phrase in phrases)
    cleaned = []
    seen = set()
    for text, topic in rows:
        key = ' '.join(tokenize(text))
        if not key or (key, topic) in seen:
            continue
        seen.add((key, topic))
        cleaned.append((text, topic))
    return cleaned


def _split(rows):
    by_topic = {}
    for text, topic in rows:
        by_topic.setdefault(topic, []).append((text, topic))
    train, test = [], []
    for group in by_topic.values():
        cut = max(1, int(len(group) * 0.8)) if len(group) > 1 else 1
        train.extend(group[:cut])
        test.extend(group[cut:])
    if not test:
        test = list(train)
    return train, test


def train_intent():
    rows = _rows()
    if len(rows) < 8:
        raise ValueError('Not enough labeled school questions to train intent.')
    train, test = _split(rows)
    vectorizer = TfidfVectorizer().fit([text for text, _topic in train])
    model = MultinomialNB().fit(
        [vectorizer.transform_one(text) for text, _topic in train],
        [topic for _text, topic in train],
    )
    correct = 0
    for text, topic in test:
        predicted, _confidence = _argmax(vectorizer, model, text)
        if predicted == topic:
            correct += 1
    accuracy = correct / max(len(test), 1)
    return save_run(
        name='intent',
        algorithm='tfidf_multinomial_nb',
        n_train=len(train),
        n_test=len(test),
        metrics={'accuracy': round(accuracy, 4), 'topics': sorted({topic for _text, topic in rows})},
        artifact={'vectorizer': vectorizer.dump(), 'model': model.dump()},
        feature_schema={'text': 'tfidf', 'vocabulary': len(vectorizer.idf)},
        dataset={
            'rows': len(rows),
            'faq_entries': FaqEntry.objects.filter(is_active=True).count(),
            'fingerprint': faq_fingerprint(),
        },
    )


def faq_fingerprint():
    """Changes whenever an active FAQ's topic, question or keywords change."""
    rows = FaqEntry.objects.filter(is_active=True).order_by('pk').values_list('pk', 'topic', 'question', 'keywords')
    return hashlib.sha1(repr(list(rows)).encode()).hexdigest()[:12]


def is_stale(run):
    """True when the FAQs the classifier learns from changed after it was trained."""
    return run is not None and (run.dataset or {}).get('fingerprint') != faq_fingerprint()


def _argmax(vectorizer, model, question):
    scores = model.predict_proba(vectorizer.transform_one(question))
    if not scores:
        return 'other', 0.0
    return max(scores.items(), key=lambda item: item[1])


def _label(vectorizer, model, question):
    topic, confidence = _argmax(vectorizer, model, question)
    if confidence < MIN_CONFIDENCE:
        return 'other', confidence
    return topic, confidence


def classify_question(question):
    artifact = last_artifact('intent')
    if not artifact:
        return 'other', 0.0
    vectorizer = TfidfVectorizer.load(artifact.get('vectorizer'))
    model = MultinomialNB.load(artifact.get('model'))
    return _label(vectorizer, model, question)


def program_summary():
    """The programs offered this year, read live from the database for the chatbot."""
    year = SchoolYear.objects.filter(is_current=True).first()
    parts = []
    for grade_level in GRADE_LEVELS:
        programs = list(programs_for(year, grade_level)) if year else []
        if not programs:
            continue
        curriculum = curriculum_for(year, grade_level)
        label = f'{grade_level} programs' + (f' ({curriculum.name})' if curriculum else '')
        parts.append(f'{label}: ' + '; '.join(f'{row.code} - {row.name}' for row in programs) + '.')
    return ' '.join(parts)


def answers_for(topic):
    if topic == 'events':
        rows = list(FaqEntry.objects.filter(is_active=True, topic__iexact='events'))
        return [row.answer for row in rows] or [EVENT_ANSWER]
    rows = list(FaqEntry.objects.filter(is_active=True, topic__iexact=topic).values_list('answer', flat=True))
    if topic == 'programs':
        live = program_summary()
        if live:
            rows.insert(0, live)
    return rows


def matching_faq_answer(question, topic):
    """Choose the active FAQ whose question and keywords best match the visitor's wording."""
    question_terms = {
        token
        for token in tokenize(question)
        if ' ' not in token and token not in FAQ_STOP_WORDS
    }
    if not question_terms:
        return None

    best_entry = None
    best_score = (0, 0.0)
    entries = FaqEntry.objects.filter(is_active=True, topic__iexact=topic).order_by('sort_order', 'pk')
    for entry in entries:
        faq_terms = {
            token
            for text in (entry.question, *entry.keyword_list())
            for token in tokenize(text)
            if ' ' not in token and token not in FAQ_STOP_WORDS
        }
        overlap = question_terms & faq_terms
        score = (len(overlap), len(overlap) / len(question_terms))
        if score > best_score:
            best_entry = entry
            best_score = score
    return best_entry.answer if best_entry else None


def school_pack(topic):
    answers = answers_for(topic)
    return '\n'.join(answers) if answers else FALLBACK
