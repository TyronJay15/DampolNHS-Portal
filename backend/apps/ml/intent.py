import hashlib
from difflib import get_close_matches

from apps.chatbot.models import FaqEntry
from apps.ml.models import ModelRun
from apps.ml.store import save_run
from apps.ml.text import TOKEN, MultinomialNB, TfidfVectorizer, tokenize
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
        'how can i check my enrollment status',
        'paano ako mag enroll',
        'paano mag register sa portal',
        'saan makikita ang enrollment status',
        'is my enrollment approved',
        'status ng enrollment ko',
        'how to apply for senior high',
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
        'ano ang available na shs programs',
        'anong mga strand ang meron',
        'what tracks and strands can i take',
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
        'how to reset my password',
        'paano palitan ang password ko',
        'ayaw mag login ng account ko',
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
        'paano ko malalaman kung approved na ang account ko',
        'approved na ba ang registration ko',
        'bakit pending yung account ko',
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
        'where can i see my grades in the portal',
        'saan ko makikita ang grades ko',
        'pwede ko bang makita ang grades ko',
        'paano tingnan ang report card',
        'saan makikita ang marka ko',
        'how do i view my report card online',
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
    # Reports of bullying or harassment. The moderation layer routes clear reports first; these teach the
    # classifier the gentler wordings.
    'safety': (
        'how can i report bullying',
        'someone is bullying me at school',
        'who can help me if i am being bullied',
        'paano mag report ng bullying',
        'may nang aaway sa akin sa school',
        'sino ang pwede kong lapitan kung inaapi ako',
        'my classmate keeps teasing me',
        'i feel unsafe at school',
        'where do i report harassment',
        'talk to the guidance counselor',
        'i need help from the guidance office',
        'kanino ako magsusumbong',
    ),
    # Questions outside the school, kept as their own class so they are declined instead of matched to the
    # nearest school topic.
    'out_of_scope': (
        'who won the nba championship',
        'who won the game last night',
        'pba finals score',
        'is taylor swift dating anyone',
        'latest celebrity gossip',
        'sino ang jowa ng artista',
        'what is the capital of france',
        'how tall is mount everest',
        'who invented the light bulb',
        'tell me a joke',
        'write me an essay about climate change',
        'solve this math problem for me',
        'answer my homework in science',
        'gawan mo ako ng essay',
        'best laptop to buy',
        'recommend a cheap phone',
        'where can i buy shoes online',
        'what should i eat for dinner',
        'recipe for adobo',
        'who should i vote for president',
        'what do you think of the senator',
        'opinion on the election',
        'how do i get a girlfriend',
        'paano magka jowa',
        'dating advice please',
        'what is the weather today',
        'translate this sentence to japanese',
        'write python code for a game',
        'best mobile legends hero',
        'what movie should i watch',
        'how to earn money online',
        'crypto investment tips',
        'what is the meaning of life',
        'sino ang pinakamagaling na singer',
        'what time is it in new york',
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
    """Changes whenever an active FAQ's topic, question or keywords change, or the built-in phrasings do."""
    rows = FaqEntry.objects.filter(is_active=True).order_by('pk').values_list('pk', 'topic', 'question', 'keywords')
    return hashlib.sha1(repr((list(rows), PARAPHRASES)).encode()).hexdigest()[:12]


def is_stale(run):
    """True when the FAQs or phrasings the classifier learns from changed after it was trained."""
    return run is not None and (run.dataset or {}).get('fingerprint') != faq_fingerprint()


# Common spellings and short forms, mapped before classification.
VARIANTS = {
    'enrolment': 'enrollment', 'enrol': 'enroll',
    'pano': 'paano', 'panu': 'paano', 'nasan': 'nasaan', 'san': 'saan', 'puwede': 'pwede', 'ung': 'yung',
    'grado': 'grades', 'marka': 'grades', 'pasword': 'password', 'pw': 'password', 'acct': 'account',
    'acc': 'account', 'pls': 'please', 'u': 'you', 'ur': 'your', 'located': 'location', 'locate': 'location',
}
SPELLING_CUTOFF = 0.8  # difflib similarity for correcting an unknown word to a known one
SPELLING_MIN_LENGTH = 4  # shorter words are too easy to confuse


def _spell(question, vectorizer):
    """Map variants, then correct unknown words of four letters or more to the closest word the model knows
    (enrolment -> enrollment, staus -> status, pasword -> password)."""
    known = [token for token in vectorizer.idf if ' ' not in token]
    fixed = []
    for word in TOKEN.findall(str(question or '').lower()):
        word = VARIANTS.get(word, word)
        if word not in vectorizer.idf and len(word) >= SPELLING_MIN_LENGTH:
            close = get_close_matches(word, known, n=1, cutoff=SPELLING_CUTOFF)
            word = close[0] if close else word
        fixed.append(word)
    return ' '.join(fixed)


_loaded = {'key': None, 'parts': (None, None)}


def _load():
    """The latest trained vectorizer and model, parsed once per training run and kept in this process."""
    runs = ModelRun.objects.filter(name='intent').order_by('-trained_at', '-id')
    latest = runs.values_list('id', 'trained_at').first()
    if latest is None:
        return None, None
    if _loaded['key'] != latest:
        artifact = ModelRun.objects.get(pk=latest[0]).artifact or {}
        _loaded['parts'] = (TfidfVectorizer.load(artifact.get('vectorizer')), MultinomialNB.load(artifact.get('model')))
        _loaded['key'] = latest
    return _loaded['parts']


def rank_topics(question):
    """Every topic with its probability, best first, after spelling correction. Empty when no model is trained."""
    vectorizer, model = _load()
    if vectorizer is None:
        return []
    scores = model.predict_proba(vectorizer.transform_one(_spell(question, vectorizer)))
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def known_words(question):
    """The question's words (after spelling correction) that the trained model has seen."""
    vectorizer, _model = _load()
    if vectorizer is None:
        return set()
    return {word for word in _spell(question, vectorizer).split() if word in vectorizer.idf}


def _argmax(vectorizer, model, question):
    scores = model.predict_proba(vectorizer.transform_one(question))
    if not scores:
        return 'other', 0.0
    return max(scores.items(), key=lambda item: item[1])


def classify_question(question):
    ranked = rank_topics(question)
    if not ranked:
        return 'other', 0.0
    topic, confidence = ranked[0]
    if confidence < MIN_CONFIDENCE:
        return 'other', confidence
    return topic, confidence


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
    entry = best_faq_entry(question, topic)
    return entry.answer if entry else None


def corrected(question):
    """The question with variants mapped and misspellings corrected against the trained vocabulary."""
    vectorizer, _model = _load()
    return _spell(question, vectorizer) if vectorizer is not None else str(question or '')


def best_faq_entry(question, topic):
    """The active FAQ of one topic that shares the most words with the question, or None when none shares any."""
    return faq_match(question, topic)[0]


def faq_match(question, topic):
    """(entry, shared words, share of the question's words) for the active FAQ of one topic that shares the most
    words with the question; (None, 0, 0.0) when none shares any."""
    question_terms = {
        token
        for token in tokenize(question)
        if ' ' not in token and token not in FAQ_STOP_WORDS
    }
    if not question_terms:
        return None, 0, 0.0

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
    return best_entry, best_score[0], best_score[1]


def school_pack(topic):
    answers = answers_for(topic)
    return '\n'.join(answers) if answers else FALLBACK
