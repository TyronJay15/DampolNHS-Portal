"""Seed for ml.CollegeProgram: college course profiles in the student skill space.

These are curated profiles, not learned from student outcomes. Runtime code
reads CollegeProgram from the database; this file only seeds it.
"""

# Seed for CollegeProgram.shs_programs: SHS programs that lead naturally to each course.
SHS_PROGRAMS = {
    'bsce': ('STEMC', 'STEM'),
    'bscs': ('STEMC', 'STEM', 'ICTP', 'ICT'),
    'bsit': ('STEMC', 'STEM', 'ICTP', 'ICT'),
    'bsn': ('STEMC', 'STEM'),
    'bsbio': ('STEMC', 'STEM'),
    'bsarch': ('STEMC', 'STEM'),
    'bsa': ('BE', 'ABM'),
    'bsba': ('BE', 'ABM'),
    'bsentrep': ('BE', 'ABM'),
    'bacom': ('ASH', 'HUMSS'),
    'bapols': ('ASH', 'HUMSS'),
    'bspsy': ('ASH', 'HUMSS'),
    'bsed': ('ASH', 'HUMSS'),
    'bshrm': ('HT', 'HE'),
    'bstm': ('HT', 'HE'),
    'bsindtech': ('HT', 'HE', 'ICTP', 'ICT', 'STEMC', 'STEM'),
}

COURSES = (
    {
        'code': 'bsce',
        'name': 'BS Civil Engineering',
        'profile': {'math': 90, 'science': 88, 'language': 70, 'tech': 70},
        'floors': {'math': 85, 'science': 83},
    },
    {
        'code': 'bscs',
        'name': 'BS Computer Science',
        'profile': {'math': 88, 'science': 72, 'language': 70, 'tech': 92},
        'floors': {'math': 83, 'tech': 80},
    },
    {
        'code': 'bsit',
        'name': 'BS Information Technology',
        'profile': {'math': 78, 'science': 68, 'language': 70, 'tech': 90},
        'floors': {'tech': 80},
    },
    {
        'code': 'bsn',
        'name': 'BS Nursing',
        'profile': {'math': 75, 'science': 90, 'language': 78, 'service': 75, 'research': 80},
        'floors': {'science': 85},
    },
    {
        'code': 'bsbio',
        'name': 'BS Biology',
        'profile': {'math': 78, 'science': 92, 'language': 70, 'research': 88},
        'floors': {'science': 85},
    },
    {
        'code': 'bsarch',
        'name': 'BS Architecture',
        'profile': {'math': 82, 'science': 70, 'arts': 85},
        'floors': {'math': 80, 'arts': 75},
    },
    {
        'code': 'bsa',
        'name': 'BS Accountancy',
        'profile': {'math': 90, 'business': 90, 'language': 75},
        'floors': {'math': 85, 'business': 80},
    },
    {
        'code': 'bsba',
        'name': 'BS Business Administration',
        'profile': {'math': 75, 'business': 88, 'language': 80},
        'floors': {'business': 80},
    },
    {
        'code': 'bsentrep',
        'name': 'BS Entrepreneurship',
        'profile': {'business': 86, 'language': 76, 'service': 70},
        'floors': {'business': 78},
    },
    {
        'code': 'bacom',
        'name': 'BA Communication',
        'profile': {'language': 91, 'social': 88, 'arts': 78, 'math': 75, 'science': 70, 'research': 80},
        'floors': {'language': 80},
    },
    {
        'code': 'bapols',
        'name': 'BA Political Science',
        'profile': {'social': 91, 'language': 86, 'math': 65, 'science': 60, 'research': 82},
        'floors': {'social': 80, 'language': 78},
    },
    {
        'code': 'bspsy',
        'name': 'BS Psychology',
        'profile': {'social': 85, 'science': 80, 'language': 78, 'math': 65, 'research': 84},
        'floors': {'social': 78},
    },
    {
        'code': 'bsed',
        'name': 'Bachelor of Secondary Education',
        'profile': {'language': 86, 'social': 84, 'math': 70, 'science': 68, 'research': 80},
        'floors': {'language': 78},
    },
    {
        'code': 'bshrm',
        'name': 'BS Hospitality Management',
        'profile': {'service': 90, 'business': 78, 'language': 75},
        'floors': {'service': 80},
    },
    {
        'code': 'bstm',
        'name': 'BS Tourism Management',
        'profile': {'service': 85, 'language': 82, 'business': 70},
        'floors': {'service': 78, 'language': 75},
    },
    {
        'code': 'bsindtech',
        'name': 'BS Industrial Technology',
        'profile': {'tech': 86, 'service': 75, 'math': 72},
        'floors': {'tech': 78},
    },
)

# Seed for ml.ProgramFamily: broad, editable groups of college programs.
FAMILIES = (
    ('computing', 'Computing & Information Technology'),
    ('engineering', 'Engineering & Architecture'),
    ('health', 'Health & Medical Sciences'),
    ('business', 'Business & Accounting'),
    ('education', 'Education'),
    ('sciences', 'Sciences & Mathematics'),
    ('social-sciences', 'Social Sciences & Humanities'),
    ('arts-media', 'Arts, Media & Communication'),
    ('hospitality', 'Hospitality & Tourism'),
    ('agriculture', 'Agriculture & Environment'),
    ('public-service', 'Public Service & Criminal Justice'),
)

# Seed for ml.FamilyInterestMap. A starting proposal from the general meaning of the six Holland types,
# not a published crosswalk; the school panel approves or edits it in the admin screen.
FAMILY_INTERESTS = {
    'computing': ('I', 'C'),
    'engineering': ('R', 'I'),
    'health': ('S', 'I'),
    'business': ('E', 'C'),
    'education': ('S', 'A'),
    'sciences': ('I',),
    'social-sciences': ('S', 'A'),
    'arts-media': ('A', 'E'),
    'hospitality': ('E', 'S'),
    'agriculture': ('R', 'I'),
    'public-service': ('S', 'E'),
}

# Seed for CollegeProgram.family.
COURSE_FAMILIES = {
    'bsce': 'engineering',
    'bscs': 'computing',
    'bsit': 'computing',
    'bsn': 'health',
    'bsbio': 'sciences',
    'bsarch': 'engineering',
    'bsa': 'business',
    'bsba': 'business',
    'bsentrep': 'business',
    'bacom': 'arts-media',
    'bapols': 'social-sciences',
    'bspsy': 'social-sciences',
    'bsed': 'education',
    'bshrm': 'hospitality',
    'bstm': 'hospitality',
    'bsindtech': 'engineering',
}
