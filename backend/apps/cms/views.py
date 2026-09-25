from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.cms.models import SiteContent


def clean_payload(document, payload):
    if document != SiteContent.Document.LANDING or not isinstance(payload, dict):
        return payload
    cleaned = dict(payload)
    cleaned.pop('bulletinCards', None)
    return cleaned


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
        payload = clean_payload(document, payload)
        row, _created = SiteContent.objects.update_or_create(
            document=document,
            defaults={'payload': payload, 'updated_by': request.user},
        )
        audit.record(
            user=request.user,
            action='cms_save',
            summary=f'Saved CMS document {document}',
            target_type='SiteContent',
            target_id=row.id,
        )
        return Response({'document': row.document, 'payload': row.payload})
