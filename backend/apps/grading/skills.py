from collections import defaultdict
from decimal import Decimal

from apps.grading.scores import average

SKILLS = (
    ('math', 'Math'),
    ('science', 'Science'),
    ('language', 'Language'),
    ('social', 'Social'),
    ('arts', 'Arts'),
    ('business', 'Business'),
    ('tech', 'Tech'),
    ('service', 'Service'),
)

SKILL_LABELS = dict(SKILLS)

SUBJECT_SKILL = {
    'gen-math': 'math',
    'finite-1': 'math',
    'finite-2': 'math',
    'math': 'math',
    'gen-sci': 'science',
    'bio-1': 'science',
    'bio-2': 'science',
    'chem-1': 'science',
    'chem-2': 'science',
    'phys-1': 'science',
    'phys-2': 'science',
    'ess-1': 'science',
    'ess-2': 'science',
    'drrr': 'science',
    'phys-sci': 'science',
    'gen-phys-1': 'science',
    'gen-phys-2': 'science',
    'gen-bio-1': 'science',
    'gen-bio-2': 'science',
    'gen-chem-2': 'science',
    'sci': 'science',
    'eff-comm': 'language',
    'mab-kom': 'language',
    'contemp-lit-1': 'language',
    'creative-comp-1': 'language',
    'filipino-1': 'language',
    'malikhaing': 'language',
    'lit-21': 'language',
    'mil': 'language',
    'fil-piling': 'language',
    'creative-writing': 'language',
    'creative-nonfic': 'language',
    'eng': 'language',
    'fil': 'language',
    'kasaysayan': 'social',
    'life-career': 'social',
    'citizenship': 'social',
    'intro-philo': 'social',
    'ph-governance': 'social',
    'soc-sci': 'social',
    'diass': 'social',
    'trends-21': 'social',
    'cesc': 'social',
    'ap': 'social',
    'arts-1': 'arts',
    'arts-2': 'arts',
    'fil-identity': 'arts',
    'arts-leadership': 'arts',
    'animation': 'arts',
    'bus-1': 'business',
    'intro-org-mgmt': 'business',
    'bus-2': 'business',
    'bus-3': 'business',
    'contemp-mktg': 'business',
    'entrep': 'business',
    'applied-econ': 'business',
    'org-mgmt': 'business',
    'prin-mktg': 'business',
    'bus-fin': 'business',
    'bus-ethics': 'business',
    'bus-sim': 'business',
    'emtech': 'tech',
    'broadband': 'tech',
    'prog-java': 'tech',
    'prog-dotnet': 'tech',
    'prog-oracle': 'tech',
    'css': 'tech',
    'contact-center': 'tech',
    'ict-prog': 'tech',
    'tech-draft': 'tech',
    'bakery': 'service',
    'events-mgmt': 'service',
    'fb-operation': 'service',
    'hotel-front': 'service',
    'hotel-hk': 'service',
    'kitchen-ops': 'service',
    'tourism-svc': 'service',
    'cookery': 'service',
    'bread-pastry': 'service',
    'fb-services': 'service',
    'housekeeping': 'service',
    'work-immersion': 'service',
}


def skill_vector(grades):
    buckets = defaultdict(list)
    for row in grades:
        if row is None:
            continue
        subject = getattr(row, 'subject', None)
        code = getattr(subject, 'code', None)
        skill = SUBJECT_SKILL.get(code)
        if skill is None:
            continue
        buckets[skill].append(Decimal(str(row.score)))
    return {skill: average(values) for skill, values in buckets.items()}


def skill_rows(vector):
    return [
        {'key': key, 'label': SKILL_LABELS[key], 'average': str(vector[key])}
        for key, _label in SKILLS
        if key in vector
    ]


def overall_average(grades):
    return average([Decimal(str(row.score)) for row in grades if row is not None])
