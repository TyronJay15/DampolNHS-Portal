from django.db import models


class ChatQuestion(models.Model):
    question = models.CharField(max_length=400)
    topic = models.CharField(max_length=32, db_index=True)
    confidence = models.FloatField(default=0)
    source = models.CharField(max_length=16, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ml_chat_question'
        ordering = ['-created_at']


class ClusterSnapshot(models.Model):
    school_year = models.ForeignKey(
        'school.SchoolYear',
        on_delete=models.CASCADE,
        related_name='cluster_snapshots',
    )
    cluster_code = models.CharField(max_length=16)
    applied_count = models.PositiveIntegerField(default=0)
    approved_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'ml_cluster_snapshot'
        unique_together = ('school_year', 'cluster_code')
        ordering = ['school_year_id', 'cluster_code']


class ModelRun(models.Model):
    name = models.CharField(max_length=32, db_index=True)
    algorithm = models.CharField(max_length=64)
    n_train = models.PositiveIntegerField(default=0)
    n_test = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(default=dict)
    artifact = models.JSONField(default=dict)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ml_model_run'
        ordering = ['-trained_at']
