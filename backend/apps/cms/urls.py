from django.urls import path

from .media_views import CmsMediaView
from .views import SiteContentView

urlpatterns = [
    path('content/', SiteContentView.as_view(), name='cms-content'),
    path('media/', CmsMediaView.as_view(), name='cms-media'),
]
