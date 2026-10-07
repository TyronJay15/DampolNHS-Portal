from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class InvalidId(APIException):
    status_code = 400
    default_detail = 'An id in the request is not a valid number.'
    default_code = 'invalid_id'


def _bad_lookup_value(exc):
    """Django's own error for a non-numeric id in a query ("Field 'id' expected a number but got 'abc'").

    Only this exact message is turned into a 400; any other ValueError is a real bug and stays a 500.
    """
    message = str(exc)
    return isinstance(exc, (ValueError, TypeError)) and message.startswith('Field ') and ' expected a number but got ' in message


def api_exception_handler(exc, context):
    """Return {detail, code, errors} so the frontend can show a clear message."""
    if isinstance(exc, DjangoValidationError):
        # Model-level rules (e.g. a program's grade level) answer 400, not 500.
        exc = ValidationError(exc.message_dict if hasattr(exc, 'error_dict') else exc.messages)
    elif _bad_lookup_value(exc):
        exc = InvalidId()
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    detail = data.get('detail') if isinstance(data, dict) else data
    if isinstance(detail, list):
        detail = ' '.join(str(item) for item in detail)
    elif detail is None and isinstance(data, dict):
        detail = 'Request could not be processed.'

    payload = {
        'detail': str(detail) if detail is not None else 'Request could not be processed.',
        'code': getattr(getattr(exc, 'detail', None), 'code', None)
        or getattr(exc, 'default_code', 'error'),
    }
    if isinstance(data, dict) and any(key not in ('detail',) for key in data):
        payload['errors'] = {k: v for k, v in data.items() if k != 'detail'}
    response.data = payload
    return response
