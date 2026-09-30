from django.contrib import admin

from apps.ml.models import ChatQuestion, ClusterSnapshot, CollegeOutcome, CollegeProgram, CollegeProgramSkill, ModelRun


@admin.register(ModelRun)
class ModelRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'algorithm', 'n_train', 'n_test', 'trained_at')
    list_filter = ('name',)


@admin.register(ChatQuestion)
class ChatQuestionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'source', 'created_at')
    list_filter = ('topic', 'source')


@admin.register(ClusterSnapshot)
class ClusterSnapshotAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'cluster_code', 'program', 'curriculum', 'applied_count', 'approved_count')


class CollegeProgramSkillInline(admin.TabularInline):
    model = CollegeProgramSkill
    extra = 0


@admin.register(CollegeProgram)
class CollegeProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    filter_horizontal = ('shs_programs',)
    inlines = [CollegeProgramSkillInline]


@admin.register(CollegeOutcome)
class CollegeOutcomeAdmin(admin.ModelAdmin):
    list_display = ('student', 'college_program', 'school_year', 'recorded_at')
    list_filter = ('college_program', 'school_year')
