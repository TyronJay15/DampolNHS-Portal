from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.accounts.views_health import HealthView, ReadyView
from config.admin_site import PortalAdminSite

# Every console sign-in needs the authenticator code too (django-otp), and failures are limited.
admin.site.__class__ = PortalAdminSite

urlpatterns = [
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/health/ready/', ReadyView.as_view(), name='health-ready'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/register/', include('apps.people.register_urls')),
    path('api/programs/', include('apps.school.program_urls')),
    path('api/students/', include('apps.people.student_urls')),
    path('api/teachers/', include('apps.people.teacher_urls')),
    path('api/admin/', include('apps.people.admin_urls')),
    path('api/sections/', include('apps.school.section_urls')),
    path('api/subjects/', include('apps.school.subject_urls')),
    path('api/grades/', include('apps.grading.urls')),
    path('api/terms/', include('apps.school.term_urls')),
    path('api/access/', include('apps.access.urls')),
    path('api/school-years/', include('apps.school.year_urls')),
    path('api/announcements/', include('apps.cms.announcement_urls')),
    path('api/cms/', include('apps.cms.urls')),
    path('api/audit-logs/', include('apps.audit.urls')),
    path('api/chatbot/', include('apps.chatbot.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/ml/', include('apps.ml.urls')),
    path('api/guidance/', include('apps.guidance.urls')),
]

# The Django admin console lives at DJANGO_ADMIN_PATH (a hard-to-guess path in production), or nowhere.
if settings.DJANGO_ADMIN_PATH.lower() != 'off':
    urlpatterns.insert(0, path(f'{settings.DJANGO_ADMIN_PATH}/', admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Only the uploaded website photos are public; nothing else under MEDIA_ROOT is ever served.
    urlpatterns += [
        re_path(r'^media/(?P<path>cms/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp|gif))$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
