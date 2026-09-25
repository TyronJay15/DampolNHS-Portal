from django.contrib import admin

from .models import Registration, StudentSection, TeacherAssignment

admin.site.register(Registration)
admin.site.register(TeacherAssignment)
admin.site.register(StudentSection)
