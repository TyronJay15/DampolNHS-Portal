"""/api/access/: owners tag people and decide requests; tagged people submit and follow requests.

Students are refused on every endpoint (IsStaffUser), and the services enforce who may do what.
"""

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access import services
from apps.access.activities import ACTIVITIES, owned_by
from apps.access.models import AccessRequest, AccessTag
from apps.accounts.permissions import IsStaffUser


def _person(user):
    if user is None:
        return None
    return {
        'id': user.id,
        'name': user.get_full_name() or user.email,
        'email': user.email,
        'role': user.role,
        'role_label': user.get_role_display(),
    }


def tag_payload(tag):
    activity = ACTIVITIES.get(tag.activity)
    return {
        'id': tag.id,
        'activity': tag.activity,
        'activity_label': activity.label if activity else tag.activity,
        'work_path': activity.work_path(tag.holder.role) if activity else '',
        'holder': _person(tag.holder),
        'granted_by': _person(tag.granted_by),
        'scope': tag.scope,
        'scope_text': activity.scope_text(tag.scope) if activity else tag.scope,
        'ends_on': tag.ends_on,
        'note': tag.note,
        'state': tag.state,
        'created_at': tag.created_at,
        'closed_at': tag.closed_at,
        'closed_by': _person(tag.closed_by),
        'close_reason': tag.close_reason,
        'pending': tag.requests.filter(status=AccessRequest.Status.PENDING).count(),
    }


def request_payload(row, user):
    activity = ACTIVITIES.get(row.activity)
    return {
        'id': row.id,
        'activity': row.activity,
        'activity_label': activity.label if activity else row.activity,
        'summary': row.summary,
        'changes': row.changes,
        'note': row.note,
        'status': row.status,
        'status_label': row.get_status_display(),
        'requested_by': _person(row.requested_by),
        'scope': row.tag.scope,
        'scope_text': activity.scope_text(row.tag.scope) if activity else row.tag.scope,
        'created_at': row.created_at,
        'expires_at': row.expires_at,
        'decided_by': _person(row.decided_by),
        'decided_at': row.decided_at,
        'decision_note': row.decision_note,
        'result': row.result,
        'can_decide': row.status == AccessRequest.Status.PENDING and services.can_decide(user, row),
        'can_withdraw': row.status == AccessRequest.Status.PENDING and row.requested_by_id == user.id,
    }


def _requests():
    return AccessRequest.objects.select_related('tag', 'tag__granted_by', 'requested_by', 'decided_by')


class AccessOverviewView(APIView):
    """What the signed-in person owns (and may tag), what they hold, and how many requests wait for them."""

    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        services.expire_due()
        user = request.user
        owned = owned_by(user.role)
        pending = _requests().filter(status=AccessRequest.Status.PENDING, activity__in=[a.key for a in owned])
        return Response(
            {
                'owns': [
                    {
                        **activity.as_dict(user),
                        'holders': [_person(row) for row in services.holders_for(user, activity)],
                    }
                    for activity in owned
                ],
                'holds': [tag_payload(tag) for tag in services.live_tags(user)],
                'inbox_count': sum(1 for row in pending if services.can_decide(user, row)),
            }
        )


class AccessTagListView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        owned = [activity.key for activity in owned_by(request.user.role)]
        rows = AccessTag.objects.filter(activity__in=owned).select_related('holder', 'granted_by', 'closed_by')
        return Response([tag_payload(tag) for tag in rows if services.covers(request.user, tag)])

    def post(self, request):
        tag = services.grant(
            request.user,
            holder_id=request.data.get('holder'),
            activity_key=request.data.get('activity'),
            scope=request.data.get('scope', ''),
            ends_on=request.data.get('ends_on'),
            no_end_date=bool(request.data.get('no_end_date')),
            note=request.data.get('note', ''),
        )
        return Response(tag_payload(tag), status=201)


class AccessTagCloseView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def post(self, request, pk):
        tag = get_object_or_404(AccessTag.objects.select_related('holder', 'granted_by'), pk=pk)
        return Response(tag_payload(services.close_tag(request.user, tag, request.data.get('reason'))))


class AccessRequestListView(APIView):
    """?box=inbox (waiting for me), mine (what I submitted), decided (what owners like me decided)."""

    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        services.expire_due()
        user = request.user
        box = request.query_params.get('box') or 'inbox'
        if box == 'mine':
            rows = list(_requests().filter(requested_by=user)[:200])
        else:
            owned = [activity.key for activity in owned_by(user.role)]
            rows = _requests().filter(activity__in=owned)
            rows = rows.filter(status=AccessRequest.Status.PENDING) if box == 'inbox' else rows.exclude(
                status=AccessRequest.Status.PENDING
            )
            rows = [row for row in rows[:400] if services.covers(user, row.tag)]
            if box == 'inbox':
                rows = [row for row in rows if services.can_decide(user, row)]
        return Response([request_payload(row, user) for row in rows])

    def post(self, request):
        row = services.submit(
            request.user,
            request.data.get('activity'),
            request.data.get('payload'),
            request.data.get('note'),
        )
        return Response(request_payload(row, request.user), status=201)


class AccessRequestWithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def post(self, request, pk):
        row = get_object_or_404(_requests(), pk=pk)
        return Response(request_payload(services.withdraw(request.user, row), request.user))


class AccessRequestDecideView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def post(self, request, pk):
        row = get_object_or_404(_requests(), pk=pk)
        decided = services.decide(request.user, row, bool(request.data.get('approve')), request.data.get('note', ''))
        return Response(request_payload(decided, request.user))
