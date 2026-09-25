from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EncodeWindowHistoryView, TermViewSet

router = DefaultRouter()
router.register('', TermViewSet, basename='term')

urlpatterns = [
    path('window-history/', EncodeWindowHistoryView.as_view(), name='encode-window-history'),
] + router.urls
