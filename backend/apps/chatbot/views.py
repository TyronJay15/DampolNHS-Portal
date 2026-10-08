from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.chatbot import responses
from apps.chatbot.assistant import respond
from apps.chatbot.privacy import redact
from apps.ml.models import ChatQuestion

MAX_QUESTION = 400  # characters; longer text is refused before any check, model or Gemini sees it


class ChatbotAskView(APIView):
    """Public chatbot. Anyone may ask; a signed-in user is recognized through the normal API authentication, so
    live topics (apps.chatbot.live_data) can answer the roles allowed to see them. The message flow is in
    apps.chatbot.assistant."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'chatbot'

    def post(self, request):
        raw = request.data.get('question')
        question = raw.strip() if isinstance(raw, str) else ''
        if not question:
            return Response(
                {'answer': responses.EMPTY, 'topic': None, 'confidence': 0, 'kind': 'invalid', 'options': []}
            )
        if len(question) > MAX_QUESTION:
            return Response({'detail': f'Keep the question under {MAX_QUESTION} characters.'}, status=400)

        # From here on only the redacted text is used: it is what the checks and Gemini see and what is stored.
        question = redact(question)[:MAX_QUESTION]
        reply = respond(question, request.user)
        confidence = round(float(reply.confidence), 4)
        # The redacted question is stored, never the answer. Abuse, attacks and personal safety reports are
        # counted without their text.
        ChatQuestion.objects.create(
            question=question if reply.keep_text else '',
            topic=reply.topic,
            confidence=confidence,
            source=reply.source,
        )
        return Response(
            {
                'answer': reply.answer,
                'topic': reply.topic,
                'confidence': confidence,
                'kind': reply.kind,
                'options': list(reply.options),
            }
        )
