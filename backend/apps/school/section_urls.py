from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SectionViewSet
from .views_archive import SectionArchiveView, SectionRestoreView, SectionRosterView

router = DefaultRouter()
router.register('', SectionViewSet, basename='section')

urlpatterns = [
    path('<int:pk>/roster/', SectionRosterView.as_view(), name='section-roster'),
    path('<int:pk>/archive/', SectionArchiveView.as_view(), name='section-archive'),
    path('<int:pk>/restore/', SectionRestoreView.as_view(), name='section-restore'),
] + router.urls
