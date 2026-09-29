from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ml.gemini import phrase_answer
from apps.ml.intent import FALLBACK, answers_for, classify_question, ensure_intent, school_pack
from apps.ml.models import ChatQuestion


class ChatbotAskView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response({'answer': 'Please type a question.', 'topic': None, 'confidence': 0})

        try:
            ensure_intent()
            topic, confidence = classify_question(question)
        except ValueError:
            topic, confidence = 'other', 0.0

        pack = school_pack(topic)
        answers = answers_for(topic)
        source = 'fallback'
        answer = FALLBACK
        if topic != 'other' and answers:
            written = phrase_answer(question, topic, pack)
            if written:
                answer = written
                source = 'gemini'
            else:
                answer = answers[0]
                source = 'faq'

        ChatQuestion.objects.create(
            question=question[:400],
            topic=topic,
            confidence=round(float(confidence), 4),
            source=source,
        )
        return Response({'answer': answer, 'topic': topic, 'confidence': round(float(confidence), 4)})
