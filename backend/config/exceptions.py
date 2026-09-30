from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Return {detail, code, errors} so the frontend can show a clear message."""
    if isinstance(exc, DjangoValidationError):
        # Model-level rules (e.g. a program's grade level) answer 400, not 500.
        exc = ValidationError(exc.message_dict if hasattr(exc, 'error_dict') else exc.messages)
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
