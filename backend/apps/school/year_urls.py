from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SchoolYearViewSet
from .views_archive import SchoolYearArchiveView, SchoolYearDeleteView, SchoolYearRestoreView

router = DefaultRouter()
router.register('', SchoolYearViewSet, basename='school-year')

urlpatterns = [
    path('<int:pk>/archive/', SchoolYearArchiveView.as_view(), name='school-year-archive'),
    path('<int:pk>/restore/', SchoolYearRestoreView.as_view(), name='school-year-restore'),
    path('<int:pk>/delete/', SchoolYearDeleteView.as_view(), name='school-year-delete'),
] + router.urls
