from django.contrib import admin

from apps.ml.models import ChatQuestion, ClusterSnapshot, ModelRun


@admin.register(ModelRun)
class ModelRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'algorithm', 'n_train', 'n_test', 'trained_at')
    list_filter = ('name',)


@admin.register(ChatQuestion)
class ChatQuestionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'source', 'created_at')
    list_filter = ('topic', 'source')


@admin.register(ClusterSnapshot)
class ClusterSnapshotAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'cluster_code', 'applied_count', 'approved_count')
