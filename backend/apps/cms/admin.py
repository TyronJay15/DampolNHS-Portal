from django.contrib import admin

from .models import Announcement, SiteContent

admin.site.register(SiteContent)
admin.site.register(Announcement)
