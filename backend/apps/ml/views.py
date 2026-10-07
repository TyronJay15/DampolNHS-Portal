from collections import Counter
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.ml.intent import is_stale, train_intent
from apps.ml.models import ChatQuestion
from apps.ml.store import last_run


class AssistantStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'retrain'
    throttle_methods = ('POST',)

    def post(self, request):
        """Retrain the chatbot topic classifier on demand (admin button)."""
        try:
            run = train_intent()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        audit.record(
            user=request.user,
            action='model_trained',
            summary=f'Retrained the chatbot classifier (v{run.version})',
            target_type='ModelRun',
            target_id=run.id,
        )
        return self.get(request)

    def get(self, request):
        now = timezone.now()
        rows = list(ChatQuestion.objects.all()[:80])
        counts = Counter(ChatQuestion.objects.values_list('topic', flat=True))
        last = {}
        for row in ChatQuestion.objects.order_by('created_at'):
            last[row.topic] = row.created_at
        run = last_run('intent')
        return Response(
            {
                'intent': {
                    'ready': bool(run),
                    'algorithm': run.algorithm if run else '',
                    'accuracy': (run.metrics or {}).get('accuracy') if run else None,
                    'n_train': run.n_train if run else 0,
                    'n_test': run.n_test if run else 0,
                    'trained_at': run.trained_at if run else None,
                    'version': run.version if run else None,
                    'stale': is_stale(run),
                },
                'asked': {
                    'week': ChatQuestion.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
                    'month': ChatQuestion.objects.filter(created_at__gte=now - timedelta(days=30)).count(),
                    'total': ChatQuestion.objects.count(),
                },
                'topics': [
                    {'topic': topic, 'count': count, 'last_asked': last.get(topic)}
                    for topic, count in counts.most_common()
                ],
                'recent': [
                    {
                        'id': row.id,
                        'question': row.question,
                        'topic': row.topic,
                        'source': row.source,
                        'created_at': row.created_at,
                    }
                    for row in rows
                ],
            }
        )
