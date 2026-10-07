from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import role_or_tagged
from apps.accounts.models import User
from apps.cms.media import uploaded_name
from apps.cms.services import is_in_use

ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_BYTES = 5 * 1024 * 1024
# The first bytes of each image format. The extension and the browser's content type can be faked;
# these cannot, so a script or page renamed to .png is refused.
SIGNATURES = {
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.gif': (b'GIF87a', b'GIF89a'),
}


def is_real_image(upload, ext):
    head = upload.read(16)
    upload.seek(0)
    if ext == '.webp':
        return head[:4] == b'RIFF' and head[8:12] == b'WEBP'
    return head.startswith(SIGNATURES[ext])


# People tagged to prepare website pages or news can upload photos for their proposals; a photo only
# appears on the site once the Admin approves. They can only delete photos the live site does not use.
PHOTO_ACTIVITIES = ('edit_website_pages', 'post_news')


class CmsMediaView(APIView):
    permission_classes = [
        IsAuthenticated,
        role_or_tagged(User.Role.ADMIN, *PHOTO_ACTIVITIES, tagged_methods=('POST', 'DELETE')),
    ]
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
        if not is_real_image(upload, ext):
            return Response({'detail': 'That file is not a real JPG, PNG, WEBP, or GIF image.'}, status=400)
        stored = default_storage.save(f'cms/{uuid4().hex}{ext}', upload)
        url = f'{settings.MEDIA_URL.rstrip("/")}/{stored.replace(chr(92), "/")}'
        return Response({'url': url}, status=201)

    def delete(self, request):
        url = request.data.get('url') or request.query_params.get('url')
        name = uploaded_name(url)
        if not name:
            return Response({'detail': 'Only uploaded CMS photos can be deleted.'}, status=400)
        if request.user.role != User.Role.ADMIN and is_in_use(url):
            return Response({'detail': 'That photo is on the live website; only the Admin can remove it.'}, status=403)
        if default_storage.exists(name):
            default_storage.delete(name)
        return Response({'ok': True})
