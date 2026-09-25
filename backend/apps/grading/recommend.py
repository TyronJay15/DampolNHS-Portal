from apps.grading.knn import rank_courses
from apps.grading.skills import overall_average, skill_rows, skill_vector

METHOD = 'knn'
MIN_SKILLS = 3
ADVISORY = 'Advisory. Based on subjects shown so far. Not an admission decision.'


def _payload(*, ready, overall, skills, courses, summary):
    return {
        'method': METHOD,
        'ready': ready,
        'overall': str(overall) if overall is not None else None,
        'skills': skills,
        'courses': courses,
        'summary': summary,
        'advisory': ADVISORY,
    }


def recommend_payload(grades):
    rows = [row for row in grades if row is not None]
    overall = overall_average(rows)
    vector = skill_vector(rows)
    skills = skill_rows(vector)
    if len(vector) < MIN_SKILLS:
        return _payload(
            ready=False,
            overall=overall,
            skills=skills,
            courses=[],
            summary='Not enough shown grades yet for a college recommendation.',
        )
    courses = rank_courses(vector)
    if not courses:
        return _payload(
            ready=False,
            overall=overall,
            skills=skills,
            courses=[],
            summary='No college course met the skill pattern of these grades.',
        )
    return _payload(
        ready=True,
        overall=overall,
        skills=skills,
        courses=courses,
        summary=f'Top match: {courses[0]["name"]}. {courses[0]["reason"]}',
    )
