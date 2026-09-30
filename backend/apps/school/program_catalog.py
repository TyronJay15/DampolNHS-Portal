"""Canonical Senior High School strand copy for seed and updates.

These five Grade 12 strands and five Grade 11 clusters are the current offering.
Seed data only: runtime code reads Program, Curriculum and continues_to from the database.
"""

CURRICULA = (
    {'code': 'k12-shs', 'name': 'K to 12 Senior High School Curriculum', 'sort_order': 1},
    {'code': 'strengthened-shs', 'name': 'Strengthened Senior High School Curriculum', 'sort_order': 2},
)

# Transition state when these programs were seeded: Grade 11 clusters follow the
# Strengthened SHS curriculum, Grade 12 strands still follow the K to 12 curriculum.
CURRICULUM_BY_GRADE = {
    'Grade 11': 'strengthened-shs',
    'Grade 12': 'k12-shs',
}

PROGRAMS = [
    {
        'code': 'STEM',
        'name': 'Science, Technology, Engineering, and Mathematics',
        'summary': 'For learners who enjoy science and mathematics and are preparing for college programs in engineering, the sciences, health, or technology.',
        'description': 'STEM builds a strong foundation in mathematics and the natural sciences. Learners take advanced math and laboratory science subjects and complete a research or capstone project, developing problem-solving and analytical skills used in science and technology fields.',
        'sort_order': 1,
        'grade_level': 'Grade 12',
        'details': {
            'track': 'Academic Track',
            'subjects': [],
            'pathways': [
                'Engineering',
                'Architecture',
                'Nursing, medical technology, and other health sciences',
                'Computer science and information technology',
                'Mathematics and the natural sciences',
            ],
        },
    },
    {
        'code': 'ABM',
        'name': 'Accountancy, Business, and Management',
        'summary': 'Prepares learners for college and careers in business, finance, accounting, and entrepreneurship.',
        'description': 'ABM builds skills in accounting, business operations, and management. Learners study how organizations work, how money is recorded and used, and how to plan a small business, preparing them for business programs in college or for starting an enterprise.',
        'sort_order': 2,
        'grade_level': 'Grade 12',
        'details': {
            'track': 'Academic Track',
            'subjects': [
                'Fundamentals of Accountancy, Business, and Management',
                'Business Math',
                'Applied Economics',
                'Organization and Management',
                'Principles of Marketing',
                'Business Finance',
            ],
            'pathways': [
                'Accountancy',
                'Business administration',
                'Entrepreneurship',
                'Finance and banking',
                'Marketing',
            ],
        },
    },
    {
        'code': 'HUMSS',
        'name': 'Humanities and Social Sciences',
        'summary': 'For learners interested in people, society, and communication, preparing them for college programs in education, law, the social sciences, and the humanities.',
        'description': 'HUMSS explores human behavior, culture, society, and governance. Learners strengthen their reading, writing, speaking, and critical-thinking skills and take part in community-based activities.',
        'sort_order': 3,
        'grade_level': 'Grade 12',
        'details': {
            'track': 'Academic Track',
            'subjects': [
                'Creative Writing',
                'Introduction to World Religions and Belief Systems',
                'Philippine Politics and Governance',
                'Disciplines and Ideas in the Social Sciences',
                'Community Engagement, Solidarity, and Citizenship',
            ],
            'pathways': [
                'Education',
                'Political science and pre-law programs',
                'Psychology',
                'Communication and journalism',
                'Social work',
            ],
        },
    },
    {
        'code': 'ICT',
        'name': 'Information and Communications Technology',
        'summary': 'A TVL strand focused on computer and digital skills, such as computer systems servicing, programming, and digital media.',
        'description': 'ICT is one of the strands under the TVL track. Learners gain practical skills in setting up and maintaining computer systems, writing programs, and creating digital content. Like other TVL strands, it includes work immersion and may prepare learners for TESDA competency assessments.',
        'sort_order': 4,
        'grade_level': 'Grade 12',
        'details': {
            'track': 'TVL Track',
            'subjects': [
                'Computer Systems Servicing',
                'Programming',
                'Animation and Illustration',
                'Technical Drafting',
                'Work Immersion',
            ],
            'pathways': [
                'Information technology and computer science',
                'Multimedia arts',
                'Computer technician and IT support work',
                'Programming and web development',
            ],
        },
    },
    {
        'code': 'HE',
        'name': 'Home Economics',
        'summary': 'Culinary arts, tourism, hospitality, and fashion — practical skills for work, TESDA, or further study.',
        'description': 'Home Economics is a TVL strand. Learners train in food, hospitality, and related services through hands-on work and work immersion. Many specializations also prepare learners for TESDA competency assessments.',
        'sort_order': 5,
        'grade_level': 'Grade 12',
        'details': {
            'track': 'TVL Track',
            'subjects': [
                'Cookery',
                'Bread and Pastry Production',
                'Food and Beverage Services',
                'Housekeeping',
                'Work Immersion',
            ],
            'pathways': [
                'Culinary arts and hospitality',
                'Tourism',
                'Fashion and garment trades',
                'Starting a small food or service business',
            ],
        },
    },
    {
        'code': 'ASH',
        'name': 'Arts, Social Sciences, and Humanities',
        'summary': 'For learners interested in people, culture, the arts, and society during Grade 11, before HUMSS or related Grade 12 paths.',
        'description': 'This Grade 11 cluster introduces communication, culture, and civic life. Learners explore writing, social studies, and the humanities so they can continue to HUMSS or related Grade 12 strands with a stronger foundation.',
        'sort_order': 11,
        'grade_level': 'Grade 11',
        'details': {
            'track': 'Grade 11 Cluster',
            'subjects': [
                'Creative Writing',
                'Introduction to World Religions and Belief Systems',
                'Philippine Politics and Governance',
                'Disciplines and Ideas in the Social Sciences',
                'Community Engagement, Solidarity, and Citizenship',
            ],
            'pathways': [
                'HUMSS in Grade 12',
                'Education',
                'Communication and journalism',
                'Social work',
                'Political science and pre-law',
            ],
        },
    },
    {
        'code': 'BE',
        'name': 'Business and Entrepreneurship',
        'summary': 'For learners who want to understand business, money, and enterprise in Grade 11, before ABM in Grade 12.',
        'description': 'This Grade 11 cluster covers how organizations work, how products are marketed, and how a small business is planned. It prepares learners for ABM in Grade 12 and for college programs in business.',
        'sort_order': 12,
        'grade_level': 'Grade 11',
        'details': {
            'track': 'Grade 11 Cluster',
            'subjects': [
                'Applied Economics',
                'Organization and Management',
                'Principles of Marketing',
                'Business Math',
                'Fundamentals of Accountancy, Business, and Management',
            ],
            'pathways': [
                'ABM in Grade 12',
                'Accountancy',
                'Business administration',
                'Entrepreneurship',
                'Finance and banking',
            ],
        },
    },
    {
        'code': 'STEMC',
        'name': 'Science, Technology, Engineering, and Mathematics',
        'summary': 'For learners who enjoy science and mathematics in Grade 11, before the STEM strand in Grade 12.',
        'description': 'This Grade 11 cluster builds a foundation in math and laboratory science. Learners practice problem-solving and scientific thinking so they can continue to STEM in Grade 12.',
        'sort_order': 13,
        'grade_level': 'Grade 11',
        'details': {
            'track': 'Grade 11 Cluster',
            'subjects': [
                'Pre-Calculus',
                'General Biology',
                'General Chemistry',
                'General Physics',
                'Research',
            ],
            'pathways': [
                'STEM in Grade 12',
                'Engineering',
                'Health sciences',
                'Computer science',
                'Natural sciences',
            ],
        },
    },
    {
        'code': 'HT',
        'name': 'Hospitality and Tourism',
        'summary': 'For learners interested in food, travel, and guest services in Grade 11, before Home Economics or related TVL paths in Grade 12.',
        'description': 'This Grade 11 cluster introduces cookery, lodging, and tourism services through classroom and hands-on work. Learners may continue to HE in Grade 12 and toward TESDA or college hospitality programs.',
        'sort_order': 14,
        'grade_level': 'Grade 11',
        'details': {
            'track': 'Grade 11 Cluster',
            'subjects': [
                'Cookery',
                'Bread and Pastry Production',
                'Food and Beverage Services',
                'Tourism Promotion Services',
                'Work Immersion',
            ],
            'pathways': [
                'HE in Grade 12',
                'Culinary arts and hospitality',
                'Tourism',
                'Hotel and restaurant services',
                'Starting a small food or service business',
            ],
        },
    },
    {
        'code': 'ICTP',
        'name': 'ICT Support and Computer Programming Technologies',
        'summary': 'For learners who want computer support and programming skills in Grade 11, before the ICT strand in Grade 12.',
        'description': 'This Grade 11 cluster covers computer systems, basic programming, and digital tools. Learners gain practical ICT skills and can continue to ICT in Grade 12, work immersion, and TESDA assessments.',
        'sort_order': 15,
        'grade_level': 'Grade 11',
        'details': {
            'track': 'Grade 11 Cluster',
            'subjects': [
                'Computer Systems Servicing',
                'Programming',
                'Computer Hardware Servicing',
                'Digital media',
                'Work Immersion',
            ],
            'pathways': [
                'ICT in Grade 12',
                'IT support',
                'Programming and web development',
                'Computer science',
                'Multimedia arts',
            ],
        },
    },
]


def catalog_item(code):
    for item in PROGRAMS:
        if item['code'] == code:
            return item
    return {}


def extra_for(code):
    extra = dict(catalog_item(code).get('details') or {})
    from apps.school.subject_catalog import names_for_program

    extra['subjects'] = names_for_program(code)
    return extra


def grade_for(code):
    from apps.school.models import Program

    stored = Program.objects.filter(code=code).values_list('grade_level', flat=True).first()
    if stored:
        return stored
    return catalog_item(code).get('grade_level') or ''


# Seed for Program.continues_to.
GRADE11_TO_GRADE12 = {
    'ASH': 'HUMSS',
    'BE': 'ABM',
    'STEMC': 'STEM',
    'HT': 'HE',
    'ICTP': 'ICT',
}
