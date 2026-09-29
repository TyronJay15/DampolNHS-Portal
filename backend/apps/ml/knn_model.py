import random

from apps.grading.college_catalog import COURSES
from apps.grading.knn import _distance, _meets_floors, _reason
from apps.ml.store import last_artifact, save_run

K_CHOICES = (3, 5, 7)
BOOTSTRAP = 4
RESULTS = 3
TRACK = {
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


def _jitter(profile, floors, rng):
    vector = {}
    for skill, value in profile.items():
        noise = rng.uniform(-3.5, 3.5)
        score = min(100, max(60, float(value) + noise))
        floor = float((floors or {}).get(skill, 0))
        vector[skill] = round(max(score, floor), 2)
    return vector


def _labeled_rows():
    rng = random.Random(11)
    rows = []
    for course in COURSES:
        rows.append({'code': course['code'], 'name': course['name'], 'vector': dict(course['profile']), 'floors': course.get('floors') or {}})
        for _index in range(BOOTSTRAP):
            rows.append(
                {
                    'code': course['code'],
                    'name': course['name'],
                    'vector': _jitter(course['profile'], course.get('floors') or {}, rng),
                    'floors': course.get('floors') or {},
                }
            )
    return rows


def _precision(rows, k):
    hits = 0
    for index, probe in enumerate(rows):
        neighbors = []
        for other_index, other in enumerate(rows):
            if other_index == index:
                continue
            distance = _distance(probe['vector'], other['vector'])
            if distance is None:
                continue
            neighbors.append((distance, other['code']))
        neighbors.sort(key=lambda item: (item[0], item[1]))
        top = {code for _distance, code in neighbors[:k]}
        if probe['code'] in top:
            hits += 1
    return hits / max(len(rows), 1)


def train_knn():
    rows = _labeled_rows()
    scores = {k: _precision(rows, k) for k in K_CHOICES}
    best_k = max(K_CHOICES, key=lambda k: (scores[k], -k))
    return save_run(
        name='knn',
        algorithm='knn',
        n_train=len(rows),
        n_test=len(rows),
        metrics={'k': best_k, 'precision_at_k': {str(k): round(score, 4) for k, score in scores.items()}},
        artifact={'k': best_k, 'rows': rows},
    )


def rank_trained(student, program_code=None):
    artifact = last_artifact('knn')
    if not artifact:
        return []
    neighbors = []
    by_code = {course['code']: course for course in COURSES}
    for row in artifact.get('rows') or []:
        course = by_code.get(row['code'])
        if course is None or not _meets_floors(student, row.get('floors') or {}):
            continue
        distance = _distance(student, row['vector'])
        if distance is None:
            continue
        if program_code and program_code in TRACK.get(row['code'], ()):
            distance *= 0.85
        neighbors.append((distance, course))
    neighbors.sort(key=lambda item: (item[0], item[1]['name']))
    seen = set()
    ranked = []
    for distance, course in neighbors:
        if course['code'] in seen:
            continue
        seen.add(course['code'])
        ranked.append(
            {
                'code': course['code'],
                'name': course['name'],
                'distance': round(distance, 2),
                'reason': _reason(student, course),
            }
        )
        if len(ranked) == RESULTS:
            break
    return ranked
