from django.db import models


class FaqEntry(models.Model):
    topic = models.CharField(max_length=64, db_index=True)
    keywords = models.CharField(
        max_length=255,
        help_text='Comma-separated phrases used to match a visitor question.',
    )
    question = models.CharField(max_length=200)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'chatbot_faq'
        ordering = ['sort_order', 'topic']

    def keyword_list(self):
        return [part.strip().lower() for part in self.keywords.split(',') if part.strip()]

    def __str__(self):
        return self.question
