"""Official Grade 11 SSHS and Grade 12 old-curriculum subjects.

Cores are stored once and linked to every matching program. Electives and
specialized subjects attach only to their cluster or strand. term is 1, 2, 3
or None (year-long / all terms). Prerequisites are listed nowhere here.
"""

LEGACY_SUBJECT_CODES = ('eng', 'fil', 'math', 'sci', 'ap')

G11_PROGRAMS = ('ASH', 'BE', 'STEMC', 'HT', 'ICTP')
G12_PROGRAMS = ('STEM', 'ABM', 'HUMSS', 'ICT', 'HE')
G12_ACADEMIC = ('STEM', 'ABM', 'HUMSS')

SUBJECTS = (
    ('eff-comm', 'Effective Communication'),
    ('mab-kom', 'Mabisang Komunikasyon'),
    ('gen-math', 'General Mathematics'),
    ('gen-sci', 'General Science'),
    ('life-career', 'Life and Career Skills'),
    ('kasaysayan', 'Pag-aaral ng Kasaysayan at Lipunang Pilipino'),
    ('arts-1', 'Arts 1 (Creative Industries - Visual, Literary, Media, Applied, Traditional)'),
    ('arts-2', 'Arts 2 (Creative Industries - Music, Dance, Theater)'),
    ('citizenship', 'Citizenship and Civic Engagement'),
    ('contemp-lit-1', 'Contemporary Literature 1'),
    ('creative-comp-1', 'Creative Composition 1'),
    ('filipino-1', 'Filipino 1 (Wika at Komunikasyon sa Akademikong Filipino)'),
    ('fil-identity', 'Filipino Identity Through the Arts'),
    ('intro-philo', 'Introduction to Philosophy'),
    ('arts-leadership', 'Leadership and Management in the Arts'),
    ('malikhaing', 'Malikhaing Pagsulat'),
    ('ph-governance', 'Philippine Governance (Philippine Politics and Governance)'),
    ('soc-sci', 'Social Sciences (Theory and Practice)'),
    ('bus-1', 'Business 1 (Basic Accounting)'),
    ('intro-org-mgmt', 'Introduction to Organization and Management'),
    ('bus-2', 'Business 2 (Business Finance and Income Taxation)'),
    ('bus-3', 'Business 3 (Business Economics)'),
    ('contemp-mktg', 'Contemporary Marketing'),
    ('bio-1', 'Biology 1'),
    ('bio-2', 'Biology 2'),
    ('chem-1', 'Chemistry 1'),
    ('chem-2', 'Chemistry 2'),
    ('phys-1', 'Physics 1'),
    ('phys-2', 'Physics 2'),
    ('ess-1', 'Earth and Space Science 1'),
    ('ess-2', 'Earth and Space Science 2'),
    ('finite-1', 'Finite Mathematics 1'),
    ('finite-2', 'Finite Mathematics 2'),
    ('emtech', 'Empowerment Technologies'),
    ('bakery', 'Bakery Operations'),
    ('events-mgmt', 'Events Management Services'),
    ('fb-operation', 'Food and Beverage Operation'),
    ('hotel-front', 'Hotel Operation (Front Office Services)'),
    ('hotel-hk', 'Hotel Operation (Housekeeping Services)'),
    ('kitchen-ops', 'Kitchen Operations'),
    ('tourism-svc', 'Tourism Services'),
    ('broadband', 'Broadband Installation'),
    ('prog-java', 'Computer Programming (Java)'),
    ('prog-dotnet', 'Computer Programming (.NET Technology)'),
    ('prog-oracle', 'Computer Programming (Oracle Database)'),
    ('css', 'Computer Systems Servicing'),
    ('contact-center', 'Contact Center Services'),
    ('lit-21', '21st Century Literature from the Philippines and the World'),
    ('mil', 'Media and Information Literacy'),
    ('peh', 'Physical Education and Health'),
    ('drrr', 'Disaster Readiness and Risk Reduction'),
    ('phys-sci', 'Physical Science'),
    ('pr2', 'Practical Research 2'),
    ('entrep', 'Entrepreneurship'),
    ('fil-piling', 'Pagsulat sa Filipino sa Piling Larangan'),
    ('iii', 'Inquiries, Investigations and Immersion'),
    ('gen-phys-1', 'General Physics 1'),
    ('gen-phys-2', 'General Physics 2'),
    ('gen-bio-1', 'General Biology 1'),
    ('gen-bio-2', 'General Biology 2'),
    ('gen-chem-2', 'General Chemistry 2'),
    ('capstone', 'Research / Capstone Project'),
    ('applied-econ', 'Applied Economics'),
    ('org-mgmt', 'Organization and Management'),
    ('prin-mktg', 'Principles of Marketing'),
    ('bus-fin', 'Business Finance'),
    ('bus-ethics', 'Business Ethics and Social Responsibility'),
    ('bus-sim', 'Business Enterprise Simulation'),
    ('creative-writing', 'Creative Writing / Malikhaing Pagsulat'),
    ('creative-nonfic', 'Creative Nonfiction'),
    ('diass', 'Disciplines and Ideas in the Applied Social Sciences'),
    ('trends-21', 'Trends, Networks, and Critical Thinking in the 21st Century Culture'),
    ('cesc', 'Community Engagement, Solidarity, and Citizenship'),
    ('culminating', 'Culminating Activity'),
    ('ict-prog', 'Programming'),
    ('animation', 'Animation and Illustration'),
    ('tech-draft', 'Technical Drafting'),
    ('work-immersion', 'Work Immersion'),
    ('cookery', 'Cookery'),
    ('bread-pastry', 'Bread and Pastry Production'),
    ('fb-services', 'Food and Beverage Services'),
    ('housekeeping', 'Housekeeping'),
)

SUBJECT_NAMES = {code: name for code, name in SUBJECTS}

CORE = 'core'
ELECTIVE = 'elective'
APPLIED = 'applied'
SPECIALIZED = 'specialized'


def _links():
    rows = []
    for program in G11_PROGRAMS:
        for code in (
            'eff-comm',
            'mab-kom',
            'gen-math',
            'gen-sci',
            'life-career',
            'kasaysayan',
        ):
            rows.append((program, code, CORE, None))

    for code in (
        'arts-1',
        'arts-2',
        'citizenship',
        'contemp-lit-1',
        'creative-comp-1',
        'filipino-1',
        'fil-identity',
        'intro-philo',
        'arts-leadership',
        'malikhaing',
        'ph-governance',
        'soc-sci',
    ):
        rows.append(('ASH', code, ELECTIVE, None))

    for code in ('bus-1', 'intro-org-mgmt', 'bus-2', 'bus-3', 'contemp-mktg'):
        rows.append(('BE', code, ELECTIVE, None))

    for code in (
        'bio-1',
        'bio-2',
        'chem-1',
        'chem-2',
        'phys-1',
        'phys-2',
        'ess-1',
        'ess-2',
        'finite-1',
        'finite-2',
        'emtech',
    ):
        rows.append(('STEMC', code, ELECTIVE, None))

    for code in (
        'bakery',
        'events-mgmt',
        'fb-operation',
        'hotel-front',
        'hotel-hk',
        'kitchen-ops',
        'tourism-svc',
    ):
        rows.append(('HT', code, ELECTIVE, None))

    for code in (
        'broadband',
        'prog-java',
        'prog-dotnet',
        'prog-oracle',
        'css',
        'contact-center',
    ):
        rows.append(('ICTP', code, ELECTIVE, None))

    for program in G12_PROGRAMS:
        rows.append((program, 'lit-21', CORE, 1))
        rows.append((program, 'mil', CORE, 1))
        rows.append((program, 'peh', CORE, None))
        rows.append((program, 'pr2', APPLIED, 1))
        rows.append((program, 'entrep', APPLIED, 2))
        rows.append((program, 'fil-piling', APPLIED, 2))

    rows.append(('STEM', 'drrr', CORE, 1))
    for program in ('ABM', 'HUMSS', 'ICT', 'HE'):
        rows.append((program, 'phys-sci', CORE, 1))

    for program in G12_ACADEMIC:
        rows.append((program, 'iii', APPLIED, 3))

    rows.extend(
        (
            ('STEM', 'gen-phys-1', SPECIALIZED, 1),
            ('STEM', 'gen-bio-1', SPECIALIZED, 1),
            ('STEM', 'gen-chem-2', SPECIALIZED, 1),
            ('STEM', 'gen-phys-2', SPECIALIZED, 2),
            ('STEM', 'gen-bio-2', SPECIALIZED, 2),
            ('STEM', 'capstone', SPECIALIZED, 3),
            ('ABM', 'applied-econ', SPECIALIZED, 1),
            ('ABM', 'org-mgmt', SPECIALIZED, 1),
            ('ABM', 'prin-mktg', SPECIALIZED, 1),
            ('ABM', 'bus-fin', SPECIALIZED, 2),
            ('ABM', 'bus-ethics', SPECIALIZED, 2),
            ('ABM', 'bus-sim', SPECIALIZED, 3),
            ('HUMSS', 'creative-writing', SPECIALIZED, 1),
            ('HUMSS', 'diass', SPECIALIZED, 1),
            ('HUMSS', 'cesc', SPECIALIZED, 1),
            ('HUMSS', 'creative-nonfic', SPECIALIZED, 2),
            ('HUMSS', 'trends-21', SPECIALIZED, 2),
            ('HUMSS', 'culminating', SPECIALIZED, 3),
            ('ICT', 'css', SPECIALIZED, 1),
            ('ICT', 'ict-prog', SPECIALIZED, 2),
            ('ICT', 'animation', SPECIALIZED, 2),
            ('ICT', 'tech-draft', SPECIALIZED, 3),
            ('ICT', 'work-immersion', SPECIALIZED, 3),
            ('HE', 'cookery', SPECIALIZED, 1),
            ('HE', 'bread-pastry', SPECIALIZED, 1),
            ('HE', 'fb-services', SPECIALIZED, 2),
            ('HE', 'housekeeping', SPECIALIZED, 2),
            ('HE', 'work-immersion', SPECIALIZED, 3),
        )
    )
    return tuple(rows)


PROGRAM_SUBJECTS = _links()


def names_for_program(code):
    return [SUBJECT_NAMES[subject] for program, subject, _kind, _term in PROGRAM_SUBJECTS if program == code]


# Seed for SkillDomain and Subject.skill_domain. Order is the ML feature order.
SKILL_DOMAINS = (
    ('math', 'Math'),
    ('science', 'Science'),
    ('language', 'Language'),
    ('social', 'Social'),
    ('arts', 'Arts'),
    ('business', 'Business'),
    ('tech', 'Tech'),
    ('service', 'Service'),
    ('research', 'Research'),
)

# Seed for Subject.matching_excluded: PE and Health say little about college fit.
MATCHING_EXCLUDED = ('peh',)

SUBJECT_DOMAIN = {
    'pr2': 'research',
    'iii': 'research',
    'capstone': 'research',
    'culminating': 'research',
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
