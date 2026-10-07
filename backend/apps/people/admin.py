from django.contrib import admin

from config.admin_readonly import ReadOnlyModelAdmin

from .models import Registration, StudentSection, TeacherAssignment

# Registrations, assignments and placements change only through the audited portal screens.
admin.site.register(Registration, ReadOnlyModelAdmin)
admin.site.register(TeacherAssignment, ReadOnlyModelAdmin)
admin.site.register(StudentSection, ReadOnlyModelAdmin)
