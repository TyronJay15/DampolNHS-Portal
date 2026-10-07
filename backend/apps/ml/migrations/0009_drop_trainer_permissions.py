from django.db import migrations


def drop_trainer_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(
        content_type__app_label='ml',
        codename__in=('train_recommender', 'activate_recommender'),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ml', '0008_drop_alumni_artifacts'),
    ]

    operations = [
        migrations.RunPython(drop_trainer_permissions, migrations.RunPython.noop),
    ]
