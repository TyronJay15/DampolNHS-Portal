from django.contrib import admin, messages

from apps.ml.intent import train_intent

from .models import FaqEntry


@admin.register(FaqEntry)
class FaqEntryAdmin(admin.ModelAdmin):
    """Editing FAQs retrains the chatbot so new topics and keywords are learned right away."""

    list_display = ('question', 'topic', 'is_active', 'sort_order')
    list_filter = ('topic', 'is_active')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._retrain(request)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        self._retrain(request)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        self._retrain(request)

    def _retrain(self, request):
        try:
            run = train_intent()
        except ValueError as exc:
            self.message_user(request, f'Chatbot not retrained: {exc}', level=messages.WARNING)
            return
        self.message_user(request, f'Chatbot retrained (v{run.version}).')
