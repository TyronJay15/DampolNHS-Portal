from django.utils import timezone


def encode_is_open(term, when=None):
    when = when or timezone.now()
    if term.encode_opens_at and when < term.encode_opens_at:
        return False
    if term.encode_closes_at and when >= term.encode_closes_at:
        return False
    return True


def encode_closed_response(term):
    return {'detail': f'The encode window for {term.label} is closed.'}
