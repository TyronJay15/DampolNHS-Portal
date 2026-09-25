from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import FaqEntry


class ChatbotAskView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        question = str(request.data.get('question') or '').strip().lower()
        if not question:
            return Response({'answer': 'Please type a question.'})

        best = None
        best_score = 0
        for entry in FaqEntry.objects.filter(is_active=True):
            score = 0
            for keyword in entry.keyword_list():
                if keyword and keyword in question:
                    score += len(keyword.split()) + 1
            if score > best_score:
                best_score = score
                best = entry

        if best and best_score >= 2:
            return Response({'answer': best.answer, 'topic': best.topic})
        return Response(
            {
                'answer': (
                    'I can help with registration, programs, login, account approval, '
                    'grades, and contact information. Try asking about registration or STEM.'
                ),
                'topic': None,
            }
        )
