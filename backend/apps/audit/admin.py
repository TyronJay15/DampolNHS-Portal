from django.contrib import admin

from config.admin_readonly import ReadOnlyModelAdmin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyModelAdmin):
    """Audit entries are evidence, so nobody adds, edits or deletes them here."""

    list_display = ('created_at', 'action', 'actor_label', 'actor_role', 'summary')
    list_filter = ('family', 'actor_role')
    search_fields = ('action', 'summary', 'actor_label')
