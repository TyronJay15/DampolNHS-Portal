from django.contrib import admin

from apps.ml.models import (
    ChatQuestion,
    ClusterSnapshot,
    CollegeOutcome,
    CollegeProgram,
    CollegeProgramSkill,
    ModelRun,
    ProgramFamily,
    ProgramProfileSnapshot,
    RecommenderConfig,
)
from config.admin_readonly import ReadOnlyAdminMixin, ReadOnlyModelAdmin


@admin.register(ModelRun)
class ModelRunAdmin(ReadOnlyModelAdmin):
    list_display = ('name', 'version', 'algorithm', 'status', 'n_train', 'n_test', 'trained_at')
    list_filter = ('name', 'status')


@admin.register(ChatQuestion)
class ChatQuestionAdmin(ReadOnlyModelAdmin):
    list_display = ('topic', 'source', 'created_at')
    list_filter = ('topic', 'source')


@admin.register(ClusterSnapshot)
class ClusterSnapshotAdmin(ReadOnlyModelAdmin):
    list_display = ('school_year', 'cluster_code', 'program', 'curriculum', 'applied_count', 'approved_count')


class CollegeProgramSkillInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = CollegeProgramSkill
    extra = 0


@admin.register(CollegeProgram)
class CollegeProgramAdmin(ReadOnlyModelAdmin):
    list_display = ('code', 'name', 'family', 'is_active', 'verification_status', 'profile_status', 'profile_version')
    list_filter = ('is_active', 'family', 'verification_status', 'profile_status')
    inlines = [CollegeProgramSkillInline]


@admin.register(ProgramFamily)
class ProgramFamilyAdmin(ReadOnlyModelAdmin):
    list_display = ('code', 'name', 'is_active', 'sort_order')


@admin.register(ProgramProfileSnapshot)
class ProgramProfileSnapshotAdmin(ReadOnlyModelAdmin):
    list_display = ('college_program', 'version', 'status', 'created_at')


@admin.register(RecommenderConfig)
class RecommenderConfigAdmin(ReadOnlyModelAdmin):
    list_display = ('version', 'is_approved', 'active_marker', 'created_at', 'activated_at')


@admin.register(CollegeOutcome)
class CollegeOutcomeAdmin(ReadOnlyModelAdmin):
    list_display = ('student', 'college_program', 'school_year', 'status', 'recorded_at')
    list_filter = ('college_program', 'school_year', 'status')
