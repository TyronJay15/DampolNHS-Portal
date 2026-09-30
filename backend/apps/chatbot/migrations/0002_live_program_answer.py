from django.db import migrations

OLD_ANSWER = (
    'Grade 12 strands are STEM, ABM, HUMSS, ICT, and HE. Grade 11 cluster programs are ASH, BE, STEMC, HT, '
    'and ICTP. Choose one on the Programs page, then click Register Now.'
)
NEW_ANSWER = 'See every program and its subjects on the Programs page, then click Register Now.'


def drop_fixed_program_list(apps, schema_editor):
    """The chatbot now lists programs from the database; only the untouched seed answer is replaced."""
    faq_model = apps.get_model('chatbot', 'FaqEntry')
    faq_model.objects.filter(answer=OLD_ANSWER).update(answer=NEW_ANSWER)


class Migration(migrations.Migration):
    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(drop_fixed_program_list, migrations.RunPython.noop),
    ]
