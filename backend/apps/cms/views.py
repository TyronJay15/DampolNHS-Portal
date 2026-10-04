from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.cms.models import SiteContent
from apps.cms.services import clean_payload, save_document


class SiteContentView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def get(self, request):
        rows = SiteContent.objects.all()
        return Response({row.document: clean_payload(row.document, row.payload) for row in rows})

    def patch(self, request):
        document = request.data.get('document')
        payload = request.data.get('payload')
        if document not in dict(SiteContent.Document.choices):
            return Response({'detail': 'Unknown CMS document.'}, status=400)
        if not isinstance(payload, dict):
            return Response({'detail': 'payload must be an object.'}, status=400)
        row = save_document(document, payload, request.user)
        return Response({'document': row.document, 'payload': row.payload})
