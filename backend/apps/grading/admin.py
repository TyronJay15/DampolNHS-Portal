from django.contrib import admin

from config.admin_readonly import ReadOnlyModelAdmin

from .models import CorrectionRequest, Grade, GradeHistory

# Grades change only through the encode, approve and correction screens, which keep the grade history.
admin.site.register(Grade, ReadOnlyModelAdmin)
admin.site.register(GradeHistory, ReadOnlyModelAdmin)
admin.site.register(CorrectionRequest, ReadOnlyModelAdmin)
