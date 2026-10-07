"""Link checks for website content. The browser also refuses javascript: links, but the server must not store them.

A link may be a site path ("/about", "#top") or an address with an allowed scheme: http, https, mailto or tel.
Spaces and control characters are removed before the check, because browsers ignore them inside a scheme
("java\tscript:" still runs as javascript:).
"""

import re

from rest_framework.exceptions import ValidationError

ALLOWED_SCHEMES = ('http', 'https', 'mailto', 'tel')
LINK_KEYS = {'to', 'linkto', 'href', 'url', 'link', 'image', 'src'}
_SCHEME = re.compile(r'^([a-z][a-z0-9+.-]*):')
_IGNORED = re.compile(r'[\x00-\x20\x7f]')


def is_link_key(key):
    lowered = str(key).lower()
    return lowered in LINK_KEYS or lowered.endswith(('_url', 'url', '_link', 'link'))


def is_safe_link(value):
    compact = _IGNORED.sub('', str(value or '')).lower()
    match = _SCHEME.match(compact)
    return match is None or match.group(1) in ALLOWED_SCHEMES


def unsafe_links(value, path=''):
    """Every link field in a CMS document whose scheme is not allowed, as dotted paths."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            where = f'{path}.{key}' if path else str(key)
            if isinstance(item, str) and is_link_key(key) and not is_safe_link(item):
                found.append(where)
            else:
                found.extend(unsafe_links(item, where))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(unsafe_links(item, f'{path}[{index}]'))
    return found


def require_safe_links(payload):
    bad = unsafe_links(payload)
    if bad:
        raise ValidationError(
            {'payload': f'Links must start with "/", http://, https://, mailto: or tel:. Check: {", ".join(bad[:5])}.'}
        )


def validate_link_field(value):
    if value and not is_safe_link(value):
        raise ValidationError('Links must start with "/", http://, https://, mailto: or tel:.')
    return value
