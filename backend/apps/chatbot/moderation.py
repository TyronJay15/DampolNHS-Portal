"""Layer 1 of the chatbot: content moderation, checked before any classifier, FAQ or Gemini sees the message.

check(text) returns one verdict, in this order of priority:

  injection   attempts to override the assistant's rules, or to get passwords, keys, tokens or other people's
              records. Always refused, whatever else the message says.
  self_harm   the visitor may be in danger. Answered with crisis contacts, never rejected.
  safety      a report of bullying, harassment, abuse or threats. Answered with the school's reporting route,
              never rejected, even when the report quotes offensive words someone used.
  abuse       profanity, insults aimed at someone, sexual requests, slurs and threats.
  None        nothing found; the message goes on to intent classification.

Matching works on normalized words, never raw substrings, so "class", "putahe", "titik" or "computer" are not
flagged. Normalization undoes the usual disguises: capitals, accents, leetspeak (sh1t), masking (f*ck), letters
split by spaces or dots (f u c k, f.u.c.k) and stretched letters (fuuuuck).
"""

import re
import unicodedata

# Endings an offensive word can take in English or Filipino: fucking, fucker, gagong, tangang, bitches.
SUFFIXES = ('', 's', 'es', 'ed', 'er', 'ers', 'ing', 'in', 'y', 'ng')

# Offensive wherever they appear.
PROFANITY = (
    'fuck fck fuk fvck motherfuck shit bullshit bitch asshole bastard cunt slut whore '
    'puta pota putangina potangina putanginamo tangina tngina tanginamo tanginaka punyeta pakyu pakshet '
    'kupal ulol tarantado hinayupak putragis'
).split()
# Sexual requests. "sex" alone is left out: the registration form asks for it.
SEXUAL = (
    'porn porno pornhub nude nudes naked hentai blowjob horny sexy libog malibog kantot kantutan jakol pekpek puki '
    'titi boobs'
).split()
SLURS = 'nigger nigga faggot fag chink kike tranny retard'.split()
# Insults count only next to whom they are aimed at ("bobo ka", "you are stupid", "stupid bot");
# "bobo ako sa math" and "can you explain like I'm dumb" pass.
INSULTS = (
    'stupid idiot dumb moron loser useless trash bobo boba tanga inutil gaga gago engot ugok abnoy hayop bwisit'
).split()
TARGETS = frozenset('you u ur your youre yours ka mo ikaw kayo nyo niyo bot chatbot'.split())
INSULT_REACH = 2  # words between the insult and its target

ABUSIVE_PHRASES = (
    r'\bputang ?ina\b', r'\btang ?ina\b', r'\banak ng puta\b', r'\bwalang kwenta (ka|kayo|mo)\b',
    r'\b(have|having) sex\b', r'\bsex with\b', r'\bsend (me )?nudes?\b',
    # Threats made by the visitor (threats made against the visitor are reports: see SAFETY).
    r"\b(i ?'?ll|i will|i am going to|i'?m going to|i'?m gonna|gonna)\s+"
    r'(kill|hurt|shoot|stab|bomb|beat up)\b(?! (myself|my self))',
    r'\bkill (you|u|him|her|them|everyone|my teacher|my classmate)\b', r'\bbomb (the |this )?(school|campus)\b',
    r'\bpapatayin (kita|ka|ko)\b', r'\bsasaksakin (kita|ko)\b', r'\bbubugbugin (kita|ko)\b', r'\bpa ?sa?sabugin\b',
)

INJECTION_PHRASES = (
    r'\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(instructions?|rules?|prompts?|restrictions?|'
    r'guidelines?|programming|polic(y|ies)|filters?)\b',
    r'\b(system|hidden|developer|initial) (prompt|message|instructions?)\b',
    r'\byour (instructions|prompt|system message|rules)\b',
    r'\b(jailbreak|jailbroken|developer mode|dan mode|do anything now)\b',
    r'\b(you are now|from now on you are|pretend (to be|you are)|act as (an? )?(admin|administrator|developer|system|'
    r'hacker|unrestricted))\b',
    r'\b(huwag|wag) mong sundin\b', r'\bkalimutan mo (ang|yung|ung)\b',
    r'\b(hack|hacking|crack|brute ?force|phish|phishing)\b',
    # Code-injection probes.
    r"['\"]\s*or\s+\d+\s*=\s*\d+", r'\b(drop|truncate)\s+table\b', r'\bunion\s+select\b', r'<\s*script\b',
)

# Asking to be shown a secret: "show me the administrator password", "what is the API key".
SECRET_REQUEST = re.compile(
    r'\b(show|give|reveal|tell|send|leak|dump|list|share|display|print|expose|what is|what are|whats|ibigay|ipakita|'
    r'sabihin|ano ang|ano yung)\b.{0,40}\b(passwords?|pass ?words?|api ?keys?|secret ?keys?|tokens?|credentials?|'
    r'database|db password|env|environment variables|config|configuration)\b'
)
# Asking for someone else's records: "grades of Juan", "LRN ng classmate ko", "list of all students".
RECORD_REQUEST = re.compile(
    r'\b(grades?|records?|report cards?|lrn|address|phone numbers?|contact numbers?|emails?|birthdays?|accounts?|marka)'
    r'\s+(of|ng|ni)\s+(?!(the |ang |our |aming )?(school|dampol|registrar|office|portal|campus|my|me|ko|aking)\b)\w+'
    r'|\b(list|names|records|grades|lrns?|emails|addresses) of (all |every |the )?'
    r'(students|learners|teachers|users|enrollees)\b'
)
# How-to questions about the portal ("how do I reset a teacher's password") are not requests for the secret.
HOW_TO = re.compile(r'^(how|paano|pano|panu|where|saan|san|can i|can teachers|can admins?|pwede)\b')
OWN = re.compile(r'\b(my|ko|aking|own)\b')
OTHERS = re.compile(
    r'\b(admin|administrator|teachers?|principal|registrar|others?|someone|somebody|another|everyone|all|users|'
    r'students?|ng iba|ni)\b'
)

SAFETY = re.compile(
    r'\b(bull(y|ied|ies|ying)|cyber ?bull(y|ied|ying)|binu?bully|inaapi|inaasar|'
    r'harass(ed|ing|ment)?|hina?harass|abus(e|ed|ing)|inaabuso|molest(ed|ing)?|hinipuan|hinahipuan|'
    r'(threaten(ed|ing)?|binantaan|tinakot) (me|ako|kami)|(sinasaktan|sinaktan) (ako|kami)|'
    r'(hit|hits|hurt|hurts|punched|kicked|slapped|touched|teases|teasing|mocking|mocks) me|'
    r'(kill|patayin|saktan|bugbugin) (me|ako)|'
    r'(calling|called|calls) me (names|bad names|ugly|fat|stupid|bobo|tanga|gago)|cursing at me|minumura (ako|kami)|'
    r'(report|i ?report|isumbong|magsumbong|sumbong)\b.{0,30}\b(bully|bullies|bullying|harassment|abuse|'
    r'incident|threats?|violence|nambubully))\b'
)
SELF_HARM = re.compile(
    r'\b(kill(ing)? myself|end my life|suicid(e|al)|self ?harm|cut(ting)? myself|hurt(ing)? myself|'
    r'want to die|wanna die|magpakamatay|magpapakamatay|patayin (ang )?sarili|saktan (ang )?sarili|'
    r'gusto ko na(ng)? mamatay|ayoko na(ng)? mabuhay)\b'
)


def plain(text):
    """Lower case, accents removed, leetspeak inside words undone, punctuation to spaces, spaces collapsed."""
    text = unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode().lower()
    # Only symbols between letters (sh1t, b!tch) or before letters (@sshole, $hit): "Grade 11" and "hi!" stay.
    leet = str.maketrans('013457@$!', 'oieastasi')
    disguised = r'(?<=[a-z])[013457@$!]+(?=[a-z])|(?<![a-z0-9])[@$]+(?=[a-z])'
    text = re.sub(disguised, lambda match: match.group().translate(leet), text)
    text = re.sub(r"[^a-z0-9*'\"<>=\s]", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _squeeze(word):
    """Stretched letters back to one: fuuuck -> fuck. Applied to words and to the term lists alike."""
    return re.sub(r'(.)\1+', r'\1', word)


def words(text):
    """Normalized words. Runs of single letters are joined (f u c k -> fuck) and stretched letters squeezed."""
    out, run = [], []
    for word in re.findall(r'[a-z*]+', plain(text)):
        if len(word) == 1:
            run.append(word)
            continue
        if run:
            out.append(''.join(run))
            run = []
        out.append(word)
    if run:
        out.append(''.join(run))
    return [_squeeze(word) for word in out]


def _forms(terms):
    """Every term with every allowed ending, squeezed, for exact lookups."""
    return frozenset(_squeeze(term + ending) for term in terms for ending in SUFFIXES)


_OFFENSIVE = _forms(PROFANITY + SEXUAL + SLURS)
_INSULTS = _forms(INSULTS)
_ABUSIVE = [re.compile(p) for p in ABUSIVE_PHRASES]
_INJECTION = [re.compile(p) for p in INJECTION_PHRASES]


def _is(word, forms):
    if '*' not in word:
        return word in forms
    # A masked spelling (f*ck, sh*t, b**ch) matches a listed word of the same length.
    pattern = re.compile('^' + re.escape(word).replace(r'\*', '[a-z]') + '$')
    return any(pattern.match(form) for form in forms)


def _aimed_insult(found):
    insults = [i for i, word in enumerate(found) if _is(word, _INSULTS)]
    targets = [i for i, word in enumerate(found) if word in TARGETS]
    return any(abs(i - j) <= INSULT_REACH + 1 for i in insults for j in targets)


def _asks_for_secrets(text):
    if SECRET_REQUEST.search(text) and not HOW_TO.match(text):
        return not (OWN.search(text) and not OTHERS.search(text))
    if RECORD_REQUEST.search(text):
        return not HOW_TO.match(text)
    return False


def check(text):
    """The moderation verdict for one message: 'injection', 'self_harm', 'safety', 'abuse' or None."""
    flat = plain(text)
    found = words(text)
    joined = ' '.join(found)
    if any(p.search(flat) or p.search(joined) for p in _INJECTION) or _asks_for_secrets(flat):
        return 'injection'
    if SELF_HARM.search(flat):
        return 'self_harm'
    if SAFETY.search(flat):
        return 'safety'
    if any(_is(word, _OFFENSIVE) for word in found):
        return 'abuse'
    if any(p.search(flat) or p.search(joined) for p in _ABUSIVE) or _aimed_insult(found):
        return 'abuse'
    return None
