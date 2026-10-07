"""Readable explanations rendered from structured evidence (recommender.evidence_for).

Deterministic templates only: the same evidence always gives the same sentences, and no generative AI
or outside service is involved. TEMPLATE_VERSION is saved with the text so a past explanation can be
reproduced after the wording changes.
"""

from apps.ml.knn_model import LIMITED, OTHER, TYPICAL

TEMPLATE_VERSION = 1

LABELS = {
    'strong': 'Strong Match',
    'good': 'Good Match',
    'possible': 'Possible Match',
    'limited': 'Limited Evidence',
}
INTEREST_WORDS = {'high': 'High', 'medium': 'Medium', 'low': 'Low'}


def _join(words):
    words = list(words)
    if len(words) <= 1:
        return ''.join(words)
    return f'{", ".join(words[:-1])} and {words[-1]}'


def _number(value):
    """Grades print without trailing zeros: 92.00 -> 92, 86.67 -> 86.67."""
    text = str(value)
    return text.rstrip('0').rstrip('.') if '.' in text else text


def sentences(evidence):
    lines = []
    strengths = evidence.get('strengths') or []
    if strengths:
        top = strengths[:2]
        parts = [f'{row["label"]} ({_number(row["student"])})' for row in top]
        lines.append(f'Your strongest relevant areas for this program are {_join(parts)}.')

    interest = evidence.get('interest')
    family = evidence.get('family') or {}
    if interest and interest.get('types'):
        kinds = _join(row['label'] for row in interest['types'])
        lines.append(
            f'Your interest in {kinds} activities is {INTEREST_WORDS[interest["tier"]]}. '
            f'These interests are linked to {family.get("name") or "this program family"} in the reviewed family profile.'
        )
    elif interest is None:
        lines.append('Take the interest assessment so your interests are part of this result.')

    strand = evidence.get('strand') or {}
    if strand.get('context') == TYPICAL:
        lines.append(f'Your {strand.get("group") or "SHS"} strand is a typical pathway to this program.')
    elif strand.get('context') == OTHER:
        lines.append('Students usually reach this program from a different strand. Your strand is evidence, not a limit.')

    for row in evidence.get('below_benchmark') or []:
        if row.get('official'):
            lines.append(
                f'This program lists an official requirement of {_number(row["benchmark"])} in {row["label"]} '
                f'(source: {row["source"]}). Your grade is {_number(row["student"])}.'
            )
        else:
            lines.append(
                f'Your {row["label"]} grade of {_number(row["student"])} is below the current profile benchmark of '
                f'{_number(row["benchmark"])} for this program. The program stays on your list. '
                'A benchmark is guidance, not a requirement.'
            )

    unchecked = evidence.get('unchecked') or []
    if unchecked:
        lines.append(f'Grades in {_join(row["label"] for row in unchecked)} would let this program be checked fully.')

    coverage = evidence.get('coverage') or {}
    if coverage:
        sentence = f'{coverage["observed"]} of {coverage["total"]} of this program\'s skill areas have your grades.'
        if coverage.get('status') == LIMITED:
            sentence += ' Treat this result as a rough guide.'
        lines.append(sentence)

    neighbors = evidence.get('neighbors')
    if neighbors:
        lines.append(
            f'{neighbors["count"]} of the {neighbors["k"]} nearest validated profiles were associated with '
            f'{family.get("name") or "this family"} programs.'
        )
    if evidence.get('method') == 'ml':
        lines.append('Machine learning trained on validated outcomes of past students helped order this program.')
    elif family.get('ml_supported') is False and evidence.get('hybrid'):
        lines.append('There is not yet enough past data for machine learning on this family, so profile matching placed it.')
    return lines


def explain(evidence, label):
    return {'label': LABELS[label], 'sentences': sentences(evidence), 'template_version': TEMPLATE_VERSION}
