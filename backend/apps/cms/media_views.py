from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin

ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_BYTES = 5 * 1024 * 1024


def uploaded_name(url):
    path = urlparse(str(url or '')).path.replace('\\', '/')
    prefix = settings.MEDIA_URL.rstrip('/') + '/'
    if not path.startswith(prefix):
        return ''
    name = path[len(prefix) :].lstrip('/')
    if not name.startswith('cms/') or '..' in name.split('/'):
        return ''
    return name


class CmsMediaView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'Choose a photo to upload.'}, status=400)
        ext = Path(upload.name or '').suffix.lower()
        if ext not in ALLOWED or not str(upload.content_type or '').startswith('image/'):
            return Response({'detail': 'Use a JPG, PNG, WEBP, or GIF photo.'}, status=400)
        if upload.size > MAX_BYTES:
            return Response({'detail': 'Photo must be 5 MB or smaller.'}, status=400)
        stored = default_storage.save(f'cms/{uuid4().hex}{ext}', upload)
        url = f'{settings.MEDIA_URL.rstrip("/")}/{stored.replace(chr(92), "/")}'
        return Response({'url': url}, status=201)

    def delete(self, request):
        name = uploaded_name(request.data.get('url') or request.query_params.get('url'))
        if not name:
            return Response({'detail': 'Only uploaded CMS photos can be deleted.'}, status=400)
        if default_storage.exists(name):
            default_storage.delete(name)
        return Response({'ok': True})
