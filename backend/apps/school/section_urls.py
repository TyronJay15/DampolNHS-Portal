from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SectionViewSet
from .views_archive import SectionArchiveView, SectionRestoreView, SectionRosterView
from .views_purge import SectionPurgeSummaryView, SectionPurgeView
from .views_section import SectionActivateView, SectionDetailView

router = DefaultRouter()
router.register('', SectionViewSet, basename='section')

urlpatterns = [
    path('<int:pk>/detail/', SectionDetailView.as_view(), name='section-detail'),
    path('<int:pk>/activate/', SectionActivateView.as_view(), name='section-activate'),
    path('<int:pk>/roster/', SectionRosterView.as_view(), name='section-roster'),
    path('<int:pk>/archive/', SectionArchiveView.as_view(), name='section-archive'),
    path('<int:pk>/restore/', SectionRestoreView.as_view(), name='section-restore'),
    path('<int:pk>/purge/', SectionPurgeView.as_view(), name='section-purge'),
    path('<int:pk>/purge/summary/', SectionPurgeSummaryView.as_view(), name='section-purge-summary'),
] + router.urls
