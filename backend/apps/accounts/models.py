import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone
from django_otp.models import Device, ThrottlingMixin, TimestampMixin


class PortalUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('username', email)
        extra_fields['email'] = self.normalize_email(email)
        return super().create_user(extra_fields['username'], email=extra_fields['email'], password=password, **{
            k: v for k, v in extra_fields.items() if k not in ('username', 'email')
        })

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Portal login. Role is the account type; teacher duties live in assignments."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        HEAD_TEACHER = 'head_teacher', 'Head teacher'
        ADMIN = 'admin', 'Admin'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class AccountStatus(models.TextChoices):
        PENDING_ACTIVATION = 'pending_activation', 'Pending activation'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        ARCHIVED = 'archived', 'Archived'
        REMOVED = 'removed', 'Removed'

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, db_index=True)
    approval_status = models.CharField(
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        db_index=True,
    )
    account_status = models.CharField(
        max_length=24,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    approval_note = models.CharField(max_length=255, blank=True)
    approval_updated_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = PortalUserManager()

    class Meta:
        db_table = 'accounts_users'

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def can_sign_in(self):
        return (
            self.is_active
            and self.account_status == self.AccountStatus.ACTIVE
            and self.approval_status == self.ApprovalStatus.APPROVED
        )


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    class Gender(models.TextChoices):
        FEMALE = 'female', 'Female'
        MALE = 'male', 'Male'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    lrn = models.CharField(max_length=32, unique=True, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    birthdate = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True, choices=Gender.choices)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)
    grade_level = models.CharField(max_length=32, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_student_profiles'

    def __str__(self):
        return f'{self.lrn} — {self.user.get_full_name()}'


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
    )
    employee_id = models.CharField(max_length=32, unique=True, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=32, blank=True)
    position = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_teacher_profiles'

    def __str__(self):
        return f'{self.employee_id} — {self.user.get_full_name()}'


class EmailCode(models.Model):
    class Purpose(models.TextChoices):
        ACTIVATE = 'activate', 'Activate account'
        PASSWORD = 'password', 'Change password'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_codes')
    purpose = models.CharField(max_length=16, choices=Purpose.choices, db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0, help_text='Wrong guesses so far; too many cancel the code.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_email_codes'
        ordering = ['-created_at']


class MailOutbox(models.Model):
    """Every portal email. Registration results wait here for the sender (see apps.accounts.outbox).

    Mail sent at once, such as codes, is logged without its body so the daily Brevo budget counts
    everything. A queued body is cleared once it is sent. Activation rows also record failures and
    are kept, so the Admin can see how many codes each staff member was sent.
    """

    class Kind(models.TextChoices):
        REGISTRATION = 'registration', 'Registration result'
        ACTIVATION = 'activation', 'Activation code'
        CODE = 'code', 'Password code'
        NOTICE = 'notice', 'Account notice'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    registration = models.ForeignKey(
        'people.Registration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mail_rows',
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_mail_outbox'
        ordering = ['id']
        indexes = [
            models.Index(fields=['status', 'next_attempt_at'], name='mail_outbox_due'),
            models.Index(fields=['sent_at'], name='mail_outbox_sent_at'),
        ]

    def __str__(self):
        return f'{self.kind} to {self.to_email} ({self.status})'


class AuthSession(models.Model):
    """One sign-in. Every refresh token it issues belongs to it, so ending it signs that browser out everywhere.

    The refresh token itself is never stored: only the SHA-256 of each one (SessionToken). See apps.accounts.sessions.
    """

    class EndReason(models.TextChoices):
        LOGOUT = 'logout', 'Signed out'
        IDLE = 'idle', 'Idle too long'
        EXPIRED = 'expired', 'Session time limit reached'
        PASSWORD = 'password', 'Password changed or reset'
        ACCOUNT = 'account', 'Account can no longer sign in'
        REPLAY = 'replay', 'A used refresh token came back'
        ADMIN = 'admin', 'Signed out by an administrator'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='auth_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    last_refreshed_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=20, choices=EndReason.choices, blank=True)

    class Meta:
        db_table = 'accounts_auth_sessions'
        indexes = [
            models.Index(fields=['user', 'ended_at'], name='auth_session_user_open'),
            models.Index(fields=['expires_at'], name='auth_session_expires'),
        ]

    def __str__(self):
        return f'Session {self.pk} for user {self.user_id}'

    @property
    def is_open(self):
        return self.ended_at is None and self.expires_at > timezone.now()


class SessionToken(models.Model):
    """One refresh token of a session, kept only as a hash. A token is used once; a used one coming back is a replay."""

    session = models.ForeignKey(AuthSession, on_delete=models.CASCADE, related_name='tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_session_tokens'

    def __str__(self):
        return f'Refresh token {self.pk} of session {self.session_id}'


class AuthenticatorDevice(TimestampMixin, ThrottlingMixin, Device):
    """An authenticator app (TOTP) for the second sign-in step. Required for Admin and Head Teacher accounts.

    The shared secret is stored encrypted with MFA_ENCRYPTION_KEY, never in plain text. Code checking, replay
    protection and the wrong-code back-off are django-otp's (see apps.accounts.mfa).
    """

    secret = models.TextField()
    drift = models.SmallIntegerField(default=0)
    last_t = models.BigIntegerField(default=-1)

    class Meta(Device.Meta):
        db_table = 'accounts_authenticator_devices'

    def verify_token(self, token):
        from apps.accounts.mfa import verify_totp

        return verify_totp(self, token)

    def get_throttle_factor(self):
        # Wrong codes wait 10, 20, 40, 80 ... seconds (django-otp caps the wait), so guessing is hopeless.
        return settings.MFA_THROTTLE_FACTOR


class RecoveryCode(models.Model):
    """A one-time code for signing in when the phone is lost. Only a keyed hash is stored."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recovery_codes')
    code_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_recovery_codes'

    def __str__(self):
        return f'Recovery code {self.pk} of user {self.user_id}'
