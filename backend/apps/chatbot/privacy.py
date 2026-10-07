"""Personal details are removed from chatbot questions before they are stored or sent to Gemini.

Visitors are asked not to type personal details, but some will. Email addresses and any run of nine or more digits
(an LRN, a phone number, an ID; spaces, dots or hyphens between digits are allowed) are replaced with a label.
"""

import re

EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
LONG_NUMBER = re.compile(r'(?<!\d)(?:\d[\s.-]?){8,}\d(?!\d)')


def redact(text):
    text = EMAIL.sub('[email removed]', str(text or ''))
    return LONG_NUMBER.sub('[number removed]', text)
