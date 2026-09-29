from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SchoolYearViewSet
from .views_archive import SchoolYearArchiveView, SchoolYearDeleteView, SchoolYearRestoreView
from .views_purge import SchoolYearPurgeSummaryView, SchoolYearPurgeView

router = DefaultRouter()
router.register('', SchoolYearViewSet, basename='school-year')

urlpatterns = [
    path('<int:pk>/archive/', SchoolYearArchiveView.as_view(), name='school-year-archive'),
    path('<int:pk>/restore/', SchoolYearRestoreView.as_view(), name='school-year-restore'),
    path('<int:pk>/delete/', SchoolYearDeleteView.as_view(), name='school-year-delete'),
    path('<int:pk>/purge/', SchoolYearPurgeView.as_view(), name='school-year-purge'),
    path('<int:pk>/purge/summary/', SchoolYearPurgeSummaryView.as_view(), name='school-year-purge-summary'),
] + router.urls
