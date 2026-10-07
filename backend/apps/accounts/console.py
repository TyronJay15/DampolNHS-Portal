"""Access to the Django admin console. Full access (superuser) is only for maintenance accounts; the portal
Admin gets the "Content editors" group, which can edit the chatbot FAQs and nothing else there."""

from django.contrib.auth.models import Group, Permission

CONTENT_EDITORS = 'Content editors'
CONTENT_PERMISSIONS = ('add_faqentry', 'change_faqentry', 'delete_faqentry', 'view_faqentry')


def content_editors_group():
    group, _ = Group.objects.get_or_create(name=CONTENT_EDITORS)
    group.permissions.set(Permission.objects.filter(content_type__app_label='chatbot', codename__in=CONTENT_PERMISSIONS))
    return group
