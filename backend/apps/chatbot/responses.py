"""The chatbot's fixed replies. Every message that is not answered from a verified FAQ or live data gets one of
these, word for word, so the assistant never improvises an answer, an argument or offensive wording."""

RESPECTFUL_LANGUAGE = (
    "Please use respectful language. I'm here to assist you with questions about Dampol NHS and its school portal."
)
OUT_OF_SCOPE = 'I can only assist with questions related to Dampol NHS and its portal services.'
REFUSED = "I can't process that request. I can help you with authorized Dampol NHS information and portal services."
NOT_VERIFIED = (
    "I don't have enough verified information to answer that question. "
    'Please contact the appropriate school personnel for assistance.'
)
CLARIFY = 'Did you mean one of these? Choose one, or ask again with a few more details.'
CLARIFY_GENERAL = 'What would you like to know about Dampol NHS or the portal? For example:'
EMPTY = 'Please type a question.'

GREETING = (
    "Hello! I'm the Dampol NHS Portal assistant. I can help with registration, programs, login, account approval, "
    'grades, events, and contacting the school.'
)
GREETING_FILIPINO = (
    'Magandang araw! Ako ang assistant ng Dampol NHS Portal. Matutulungan kita sa registration, programs, login, '
    'account approval, grades, events, at pakikipag-ugnayan sa paaralan.'
)
THANKS = 'You are welcome! Ask me anytime about Dampol NHS or the portal.'
THANKS_FILIPINO = 'Walang anuman! Magtanong ka lang tungkol sa Dampol NHS o sa portal.'

# Used when no active "safety" FAQ exists. Staff can replace it by adding a safety FAQ in the CMS.
SAFETY = (
    "I'm sorry you are going through this. You can report bullying, harassment, threats or abuse to your class "
    'adviser, a teacher you trust, the guidance office, or the school head. DepEd requires every school to act on '
    'these reports and keep them confidential. If you are in immediate danger, call 911. You can also reach the '
    'school through the Contact page.'
)
# Never replaced by an FAQ: a visitor at risk always gets the crisis contacts.
SELF_HARM = (
    'I am really sorry you are feeling this way, and you do not have to face it alone. Please talk to someone now: '
    'call the NCMH Crisis Hotline at 1553, or 911 if you are in immediate danger. You can also tell your adviser, '
    'a teacher you trust, or the guidance office.'
)
