from apps.grading.college_catalog import COURSES
from apps.grading.skills import SKILL_LABELS

NEIGHBORS = 5
RESULTS = 3


def _distance(student, profile):
    keys = [key for key in profile if key in student]
    if len(keys) < 2:
        return None
    total = sum((float(student[key]) - float(profile[key])) ** 2 for key in keys)
    return (total / len(keys)) ** 0.5


def _meets_floors(student, floors):
    for skill, minimum in floors.items():
        if skill not in student or float(student[skill]) < minimum:
            return False
    return True


def _reason(student, course):
    overlap = [key for key in course['profile'] if key in student]
    overlap.sort(key=lambda key: float(student[key]), reverse=True)
    strongest = overlap[:2]
    parts = [f'{SKILL_LABELS[key]} ({student[key]})' for key in strongest]
    joined = ' and '.join(parts) if parts else 'your shown grades'
    return f'Closest to {course["name"]} because {joined} match that profile.'


def rank_courses(student, neighbors=NEIGHBORS, limit=RESULTS):
    scored = []
    for course in COURSES:
        if not _meets_floors(student, course.get('floors') or {}):
            continue
        distance = _distance(student, course['profile'])
        if distance is None:
            continue
        scored.append((distance, course))
    scored.sort(key=lambda item: (item[0], item[1]['name']))
    ranked = []
    for distance, course in scored[:neighbors][:limit]:
        ranked.append(
            {
                'code': course['code'],
                'name': course['name'],
                'distance': round(distance, 2),
                'reason': _reason(student, course),
            }
        )
    return ranked
