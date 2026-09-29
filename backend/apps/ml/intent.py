from apps.chatbot.models import FaqEntry
from apps.ml.store import last_artifact, last_run, save_run
from apps.ml.text import MultinomialNB, TfidfVectorizer, tokenize

TOPICS = ('registration', 'programs', 'login', 'approval', 'grades', 'contact', 'events')
MIN_CONFIDENCE = 0.42
PARAPHRASES = {
    'registration': (
        'how to sign up',
        'create a student account',
        'where do i enroll',
        'start my registration',
        'i want to apply',
    ),
    'programs': (
        'what strands are offered',
        'difference between stem and stemc',
        'grade 11 clusters',
        'is there ict',
        'list of shs programs',
    ),
    'login': (
        'cannot sign in',
        'forgot my lrn login',
        'teacher email login',
        'how to enter the portal',
        'sign in page',
    ),
    'approval': (
        'why am i still pending',
        'when will admin approve me',
        'my registration is waiting',
        'account not approved yet',
        'rejected application',
    ),
    'grades': (
        'when will i see my report card',
        'are grades released',
        'who approves grades',
        'i cannot see my scores',
        'adviser show card',
    ),
    'contact': (
        'school phone number',
        'facebook page of the school',
        'where is the campus',
        'email the registrar',
        'how to reach dampol nhs',
    ),
    'events': (
        'upcoming school events',
        'is there an activity this week',
        'dashboard events',
        'campus calendar',
        'when is the next event',
    ),
}

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
        if topic not in TOPICS:
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
    )


def ensure_intent():
    return last_run('intent') or train_intent()


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


def answers_for(topic):
    if topic == 'events':
        rows = list(FaqEntry.objects.filter(is_active=True, topic__iexact='events'))
        return [row.answer for row in rows] or [EVENT_ANSWER]
    return list(
        FaqEntry.objects.filter(is_active=True, topic__iexact=topic).values_list('answer', flat=True)
    )


def school_pack(topic):
    answers = answers_for(topic)
    return '\n'.join(answers) if answers else FALLBACK
