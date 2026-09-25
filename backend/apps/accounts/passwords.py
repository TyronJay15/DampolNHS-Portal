import re

from rest_framework import serializers


def validate_password_strength(value):
    text = str(value or '')
    if len(text) < 8:
        raise serializers.ValidationError('Use at least 8 characters.')
    if not re.search(r'[A-Za-z]', text):
        raise serializers.ValidationError('Include at least one letter.')
    if not re.search(r'\d', text):
        raise serializers.ValidationError('Include at least one number.')
    return text
