from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ml.gemini import phrase_answer
from apps.ml.intent import FALLBACK, answers_for, classify_question, school_pack
from apps.ml.models import ChatQuestion


class ChatbotAskView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response({'answer': 'Please type a question.', 'topic': None, 'confidence': 0})

        # Prediction only: the intent model is trained by setup_school or train_intent, never here.
        topic, confidence = classify_question(question)

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
