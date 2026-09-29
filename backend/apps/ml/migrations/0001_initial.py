from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('school', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=400)),
                ('topic', models.CharField(db_index=True, max_length=32)),
                ('confidence', models.FloatField(default=0)),
                ('source', models.CharField(db_index=True, max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={'db_table': 'ml_chat_question', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ClusterSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cluster_code', models.CharField(max_length=16)),
                ('applied_count', models.PositiveIntegerField(default=0)),
                ('approved_count', models.PositiveIntegerField(default=0)),
                (
                    'school_year',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='cluster_snapshots',
                        to='school.schoolyear',
                    ),
                ),
            ],
            options={
                'db_table': 'ml_cluster_snapshot',
                'ordering': ['school_year_id', 'cluster_code'],
                'unique_together': {('school_year', 'cluster_code')},
            },
        ),
        migrations.CreateModel(
            name='ModelRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=32)),
                ('algorithm', models.CharField(max_length=64)),
                ('n_train', models.PositiveIntegerField(default=0)),
                ('n_test', models.PositiveIntegerField(default=0)),
                ('metrics', models.JSONField(default=dict)),
                ('artifact', models.JSONField(default=dict)),
                ('trained_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ml_model_run', 'ordering': ['-trained_at']},
        ),
    ]
