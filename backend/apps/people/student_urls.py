from django.urls import path

from .views_student import StudentMeView

urlpatterns = [
    path('me/', StudentMeView.as_view(), name='student-me'),
]
