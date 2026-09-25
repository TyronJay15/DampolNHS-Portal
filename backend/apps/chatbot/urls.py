from django.urls import path

from .views import ChatbotAskView

urlpatterns = [
    path('', ChatbotAskView.as_view(), name='chatbot-ask'),
]
