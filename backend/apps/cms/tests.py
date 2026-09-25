from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User

TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


class CmsMediaTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.settings = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.addCleanup(self.tmp.cleanup)
        self.admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            first_name='School',
            last_name='Admin',
            role=User.Role.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_upload_and_delete_photo(self):
        upload = SimpleUploadedFile('logo.png', TINY_PNG, content_type='image/png')
        created = self.client.post('/api/cms/media/', {'file': upload}, format='multipart')
        self.assertEqual(created.status_code, 201)
        url = created.data['url']
        self.assertTrue(url.startswith('/media/cms/'))
        deleted = self.client.delete('/api/cms/media/', {'url': url}, format='json')
        self.assertEqual(deleted.status_code, 200)

    def test_cannot_delete_bundled_default_file(self):
        response = self.client.delete(
            '/api/cms/media/',
            {'url': '/logo/logodampol.jpg'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
