from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.chatbot.live_data import is_live, live_answer
from apps.chatbot.privacy import redact
from apps.ml.gemini import phrase_answer
from apps.ml.intent import FALLBACK, answers_for, classify_question, matching_faq_answer, school_pack
from apps.ml.models import ChatQuestion

MAX_QUESTION = 400  # characters; longer text is refused before any model or Gemini sees it


class ChatbotAskView(APIView):
    """Public chatbot. Anyone may ask; a signed-in user is recognized through the normal API authentication, so
    live topics (apps.chatbot.live_data) can answer the roles allowed to see them."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'chatbot'

    def post(self, request):
        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response({'answer': 'Please type a question.', 'topic': None, 'confidence': 0})
        if len(question) > MAX_QUESTION:
            return Response({'detail': f'Keep the question under {MAX_QUESTION} characters.'}, status=400)
        # From here on only the redacted text is used: it is what Gemini sees and what is stored.
        question = redact(question)[:MAX_QUESTION]

        # Prediction only: the intent model is trained by setup_school or train_intent, never here.
        topic, confidence = classify_question(question)

        if is_live(topic):
            # Today's numbers come from the database and Django writes the sentence; Gemini never sees them.
            answer, source = live_answer(topic, request.user)
            return self._reply(question, topic, confidence, answer, source)

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
                answer = matching_faq_answer(question, topic) or answers[0]
                source = 'faq'

        return self._reply(question, topic, confidence, answer, source)

    @staticmethod
    def _reply(question, topic, confidence, answer, source):
        """Store the redacted question (never the answer) and send the reply."""
        confidence = round(float(confidence), 4)
        ChatQuestion.objects.create(question=question, topic=topic, confidence=confidence, source=source)
        return Response({'answer': answer, 'topic': topic, 'confidence': confidence})
