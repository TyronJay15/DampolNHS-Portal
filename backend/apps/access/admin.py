from django.contrib import admin

from .models import AccessRequest, AccessTag


@admin.register(AccessTag)
class AccessTagAdmin(admin.ModelAdmin):
    list_display = ('holder', 'activity', 'scope', 'ends_on', 'status', 'granted_by', 'created_at')
    list_filter = ('activity', 'status')


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('summary', 'activity', 'requested_by', 'status', 'decided_by', 'created_at')
    list_filter = ('activity', 'status')
