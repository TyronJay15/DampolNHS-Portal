import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

MODEL = 'gemini-2.0-flash'
ENDPOINT = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'

RULE = (
    'You are the Dampol 1st National High School portal assistant. '
    'Answer only from the school notes. Stay on registration, programs, login, approval, grades, events, or contact. '
    'Refuse homework, gossip, and anything outside this school. Keep the answer short.'
)


def phrase_answer(question, topic, pack):
    key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    if not key:
        return None
    body = json.dumps(
        {
            'systemInstruction': {'parts': [{'text': RULE}]},
            'contents': [
                {
                    'role': 'user',
                    'parts': [
                        {
                            'text': (
                                f'Topic: {topic}\nSchool notes:\n{pack}\n\nVisitor question: {question}\n'
                                'Reply using only those notes.'
                            )
                        }
                    ],
                }
            ],
        }
    ).encode()
    request = Request(
        f'{ENDPOINT}?key={key}',
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode())
    except (OSError, URLError, ValueError, TimeoutError):
        return None
    parts = (((payload.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [])
    text = ' '.join(str(part.get('text') or '').strip() for part in parts).strip()
    return text or None
