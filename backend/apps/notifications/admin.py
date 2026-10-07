from django.contrib import admin

from config.admin_readonly import ReadOnlyModelAdmin

from .models import Notification

admin.site.register(Notification, ReadOnlyModelAdmin)
