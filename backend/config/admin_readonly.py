"""Read-only Django admin pages for records that may only change through the portal.

The portal screens validate every change and write it to the audit log; an edit here would skip both. These pages
stay available for inspection by the maintenance accounts.
"""

from django.contrib import admin


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyModelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    pass
