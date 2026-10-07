import re

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

# Staff accounts can see many students' records, so their passwords are longer.
STUDENT_MIN_LENGTH = 10
STAFF_MIN_LENGTH = 12


def min_length_for(role):
    return STUDENT_MIN_LENGTH if role == 'student' else STAFF_MIN_LENGTH


def check_new_password(value, user, field='password'):
    """Validate a new password for this (possibly unsaved) user. Raises a DRF error keyed by `field`.

    Rules: the role's minimum length, at least one letter and one number, then Django's validators from
    AUTH_PASSWORD_VALIDATORS (too similar to the name or email, a common password, numbers only).
    """
    text = str(value or '')
    problems = []
    minimum = min_length_for(getattr(user, 'role', 'student'))
    if len(text) < minimum:
        problems.append(f'Use at least {minimum} characters.')
    if not re.search(r'[A-Za-z]', text):
        problems.append('Include at least one letter.')
    if not re.search(r'\d', text):
        problems.append('Include at least one number.')
    try:
        password_validation.validate_password(text, user)
    except DjangoValidationError as exc:
        problems.extend(message for message in exc.messages if 'too short' not in message)
    if problems:
        raise serializers.ValidationError({field: problems})
    return text
