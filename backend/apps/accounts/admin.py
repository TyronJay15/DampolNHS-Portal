from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from config.admin_readonly import ReadOnlyAdminMixin, ReadOnlyModelAdmin

from .models import AuthSession, StudentProfile, TeacherProfile, User


@admin.register(User)
class UserAdmin(ReadOnlyAdminMixin, DjangoUserAdmin):
    """Read-only: accounts change through the portal (audited) or the server commands, never here."""

    list_display = ('email', 'role', 'approval_status', 'account_status', 'is_active')
    list_filter = ('role', 'approval_status', 'account_status')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'role')}),
        ('Status', {'fields': ('approval_status', 'account_status', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
            },
        ),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(ReadOnlyModelAdmin):
    list_display = ('lrn', 'user', 'grade_level')
    search_fields = ('lrn', 'user__email')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(ReadOnlyModelAdmin):
    list_display = ('employee_id', 'user', 'position')
    search_fields = ('employee_id', 'user__email')


@admin.register(AuthSession)
class AuthSessionAdmin(ReadOnlyModelAdmin):
    """Sign-in sessions, for investigating an incident. Token hashes are not shown."""

    list_display = ('user', 'created_at', 'last_refreshed_at', 'expires_at', 'ended_at', 'end_reason')
    list_filter = ('end_reason',)
    search_fields = ('user__email',)
    fields = list_display
