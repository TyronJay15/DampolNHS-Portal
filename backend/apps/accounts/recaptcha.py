import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework import serializers

VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'


def verify_recaptcha(token):
    secret = (getattr(settings, 'RECAPTCHA_SECRET_KEY', '') or '').strip()
    if not secret:
        return
    token = (token or '').strip()
    if not token:
        raise serializers.ValidationError({'recaptcha_token': 'Please complete the reCAPTCHA.'})
    try:
        request = Request(
            VERIFY_URL,
            data=urlencode({'secret': secret, 'response': token}).encode(),
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode())
    except (OSError, URLError, ValueError):
        raise serializers.ValidationError({'recaptcha_token': 'Could not verify reCAPTCHA. Try again.'})
    if not payload.get('success'):
        raise serializers.ValidationError(
            {'recaptcha_token': 'reCAPTCHA expired or invalid. Tick the box again.'}
        )
