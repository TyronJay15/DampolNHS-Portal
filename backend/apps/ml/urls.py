from django.urls import path

from .views import AssistantStatsView

urlpatterns = [
    path('assistant/', AssistantStatsView.as_view(), name='ml-assistant'),
]
