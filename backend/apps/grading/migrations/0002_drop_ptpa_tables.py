from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL('DROP TABLE IF EXISTS ptpa_records;', migrations.RunSQL.noop),
        migrations.RunSQL('DROP TABLE IF EXISTS ptpa_grade_release_policy;', migrations.RunSQL.noop),
    ]
