from django.contrib import admin

from .models import (
    Curriculum,
    Program,
    ProgramSubject,
    SchoolYear,
    SchoolYearCurriculum,
    Section,
    SkillDomain,
    Subject,
    SubjectTermPlan,
    Term,
)

admin.site.register(SchoolYear)
admin.site.register(Term)
admin.site.register(ProgramSubject)
admin.site.register(SubjectTermPlan)
admin.site.register(Section)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'grade_level', 'curriculum', 'continues_to', 'is_active')
    list_filter = ('grade_level', 'curriculum', 'is_active')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'skill_domain', 'matching_excluded', 'is_active')
    list_filter = ('skill_domain', 'matching_excluded', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'sort_order')


@admin.register(SchoolYearCurriculum)
class SchoolYearCurriculumAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'grade_level', 'curriculum')
    list_filter = ('curriculum', 'grade_level')


@admin.register(SkillDomain)
class SkillDomainAdmin(admin.ModelAdmin):
    list_display = ('key', 'label', 'is_active', 'sort_order')
