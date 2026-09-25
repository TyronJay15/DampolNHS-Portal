from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_alter_user_managers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account_status',
            field=models.CharField(
                choices=[
                    ('pending_activation', 'Pending activation'),
                    ('active', 'Active'),
                    ('suspended', 'Suspended'),
                    ('archived', 'Archived'),
                    ('removed', 'Removed'),
                ],
                db_index=True,
                default='active',
                max_length=24,
            ),
        ),
    ]
