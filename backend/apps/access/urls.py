from django.urls import path

from .views import (
    AccessOverviewView,
    AccessRequestDecideView,
    AccessRequestListView,
    AccessRequestWithdrawView,
    AccessTagCloseView,
    AccessTagListView,
)

urlpatterns = [
    path('overview/', AccessOverviewView.as_view(), name='access-overview'),
    path('tags/', AccessTagListView.as_view(), name='access-tags'),
    path('tags/<int:pk>/close/', AccessTagCloseView.as_view(), name='access-tag-close'),
    path('requests/', AccessRequestListView.as_view(), name='access-requests'),
    path('requests/<int:pk>/withdraw/', AccessRequestWithdrawView.as_view(), name='access-request-withdraw'),
    path('requests/<int:pk>/decide/', AccessRequestDecideView.as_view(), name='access-request-decide'),
]
