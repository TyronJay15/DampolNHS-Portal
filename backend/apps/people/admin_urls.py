from django.urls import path

from apps.school.views_admin import AdminProgramDetailView, AdminProgramListView, AdminSubjectCreateView

from .views_admin import RegistrationApproveView, RegistrationListView, RegistrationRejectView
from .views_lock import AccountDeactivateView, AccountReactivateView, AccountRemoveView
from .views_forecast import Grade11ForecastView
from apps.school.views_archive import ArchiveDeskView

from .views_school import (
    AssignmentAdminDetailView,
    AssignmentAdminView,
    PlacementBulkView,
    PlacementListView,
    TeacherStaffListView,
)
from .views_staff import StaffAccountView, StaffActivationResendView

urlpatterns = [
    path('registrations/', RegistrationListView.as_view(), name='admin-registrations'),
    path(
        'registrations/<int:pk>/approve/',
        RegistrationApproveView.as_view(),
        name='admin-registration-approve',
    ),
    path(
        'registrations/<int:pk>/reject/',
        RegistrationRejectView.as_view(),
        name='admin-registration-reject',
    ),
    path('placements/', PlacementListView.as_view(), name='admin-placements'),
    path('placements/bulk/', PlacementBulkView.as_view(), name='admin-placements-bulk'),
    path('archive/', ArchiveDeskView.as_view(), name='admin-archive'),
    path('teachers/', TeacherStaffListView.as_view(), name='admin-teachers'),
    path('assignments/', AssignmentAdminView.as_view(), name='admin-assignments'),
    path('assignments/<int:pk>/', AssignmentAdminDetailView.as_view(), name='admin-assignment-detail'),
    path('staff/', StaffAccountView.as_view(), name='admin-staff'),
    path('staff/<int:pk>/resend-activation/', StaffActivationResendView.as_view(), name='admin-staff-resend'),
    path('forecast/', Grade11ForecastView.as_view(), name='admin-forecast'),
    path('accounts/<int:pk>/deactivate/', AccountDeactivateView.as_view(), name='admin-account-deactivate'),
    path('accounts/<int:pk>/reactivate/', AccountReactivateView.as_view(), name='admin-account-reactivate'),
    path('accounts/<int:pk>/remove/', AccountRemoveView.as_view(), name='admin-account-remove'),
    path('programs/', AdminProgramListView.as_view(), name='admin-programs'),
    path('programs/<int:pk>/', AdminProgramDetailView.as_view(), name='admin-program-detail'),
    path('subjects/', AdminSubjectCreateView.as_view(), name='admin-subjects'),
]
