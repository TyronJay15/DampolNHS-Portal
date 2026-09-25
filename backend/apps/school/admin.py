from django.contrib import admin

from .models import Program, ProgramSubject, SchoolYear, Section, Subject, Term

admin.site.register(SchoolYear)
admin.site.register(Term)
admin.site.register(Program)
admin.site.register(Subject)
admin.site.register(ProgramSubject)
admin.site.register(Section)
