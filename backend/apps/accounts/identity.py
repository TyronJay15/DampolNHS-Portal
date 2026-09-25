from apps.accounts.models import StudentProfile, User


def find_portal_user(identifier):
    ident = str(identifier or '').strip()
    if not ident:
        return None
    if '@' in ident:
        return User.objects.filter(email__iexact=ident).first()
    profile = StudentProfile.objects.select_related('user').filter(lrn__iexact=ident).first()
    return profile.user if profile else None
