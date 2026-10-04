from django.contrib import admin

from .models import CorrectionRequest, Grade, GradeHistory

admin.site.register(Grade)
admin.site.register(GradeHistory)
admin.site.register(CorrectionRequest)
