from django.urls import path

from .views_teacher import TeacherAssignmentListView

urlpatterns = [
    path('assignments/', TeacherAssignmentListView.as_view(), name='teacher-assignments'),
]
