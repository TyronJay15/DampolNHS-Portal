import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_mail_activation_log'),
        ('guidance', '0003_seed_dampol_instrument'),
        ('ml', '0007_seed_recommender'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('family_code', models.SlugField(max_length=32)),
                ('program_code', models.SlugField(max_length=32)),
                ('features', models.JSONField()),
                ('feature_schema', models.CharField(max_length=16)),
                ('instrument_version', models.PositiveIntegerField(blank=True, null=True)),
                ('strand_group', models.CharField(blank=True, max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('outcome', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='training_snapshot', to='ml.collegeoutcome')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_snapshots', to='accounts.studentprofile')),
            ],
            options={
                'db_table': 'guidance_training_snapshots',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='trainingsnapshot',
            index=models.Index(fields=['family_code', 'program_code'], name='guidance_train_family'),
        ),
    ]
