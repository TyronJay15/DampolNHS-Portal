import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
        ('school', '0001_initial'),
        ('grading', '0004_grade_history_duty'),
    ]

    operations = [
        migrations.CreateModel(
            name='PtpaAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attended', models.BooleanField(db_index=True, default=False)),
                ('marked_at', models.DateTimeField(auto_now=True)),
                ('marked_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ptpa_marks',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('section', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ptpa_records',
                    to='school.section',
                )),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ptpa_records',
                    to='accounts.studentprofile',
                )),
                ('term', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ptpa_records',
                    to='school.term',
                )),
            ],
            options={
                'db_table': 'grading_ptpa',
            },
        ),
        migrations.AddConstraint(
            model_name='ptpaattendance',
            constraint=models.UniqueConstraint(fields=('student', 'term'), name='one_ptpa_per_student_term'),
        ),
    ]
