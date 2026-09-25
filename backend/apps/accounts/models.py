from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


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
    lrn = models.CharField(max_length=32, unique=True, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    birthdate = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)
    grade_level = models.CharField(max_length=32, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_student_profiles'

    def __str__(self):
        return f'{self.lrn} — {self.user.get_full_name()}'

    @property
    def full_name(self):
        parts = [self.user.first_name, self.middle_name, self.user.last_name]
        return ' '.join(part for part in parts if part).strip()


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_email_codes'
        ordering = ['-created_at']
