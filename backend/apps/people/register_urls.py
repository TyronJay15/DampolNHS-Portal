from django.urls import path

from .views_register import StudentRegisterView

urlpatterns = [
    path('', StudentRegisterView.as_view(), name='student-register'),
]
