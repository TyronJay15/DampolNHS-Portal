"""Where uploaded CMS photos live, shared by the upload view and the clean-up of unused uploads."""

from urllib.parse import urlparse

from django.conf import settings


def uploaded_name(url):
    """The storage name of an uploaded CMS photo ('cms/<file>'), or '' for anything else."""
    path = urlparse(str(url or '')).path.replace(chr(92), '/')
    prefix = settings.MEDIA_URL.rstrip('/') + '/'
    if not path.startswith(prefix):
        return ''
    name = path[len(prefix) :].lstrip('/')
    if not name.startswith('cms/') or '..' in name.split('/'):
        return ''
    return name
