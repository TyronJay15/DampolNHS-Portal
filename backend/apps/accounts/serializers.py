from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.accounts.codes import check_code, consume_code, issue_code, resend_wait
from apps.accounts.identity import find_portal_user
from apps.accounts.mail import password_otp_email
from apps.accounts.models import User
from apps.accounts.passwords import validate_password_strength
from apps.accounts.recaptcha import verify_recaptcha


class AuthDenied(APIException):
    status_code = 401
    default_code = 'authentication_failed'


class CodeCooldown(APIException):
    status_code = 429
    default_code = 'code_cooldown'


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    recaptcha_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        verify_recaptcha(attrs.pop('recaptcha_token', ''))
        identifier = attrs['identifier'].strip()
        password = attrs['password']
        user = find_portal_user(identifier)

        if user is None:
            raise AuthDenied('Invalid credentials.')

        if user.account_status == User.AccountStatus.PENDING_ACTIVATION:
            raise AuthDenied(
                'Activate your account with the code sent to your email.',
                code='account_needs_activation',
            )

        if not user.has_usable_password() or not user.check_password(password):
            raise AuthDenied('Invalid credentials.')

        if user.approval_status == User.ApprovalStatus.PENDING:
            raise AuthDenied(
                'Your account is waiting for administrator approval.',
                code='account_pending',
            )
        if user.account_status in (
            User.AccountStatus.SUSPENDED,
            User.AccountStatus.ARCHIVED,
            User.AccountStatus.REMOVED,
        ):
            raise AuthDenied(
                'This account has been archived. Contact the school office.',
                code='account_deactivated',
            )
        if user.approval_status == User.ApprovalStatus.REJECTED:
            raise AuthDenied(
                'This registration was not approved. Contact the school office.',
                code='account_rejected',
            )
        if not user.can_sign_in:
            raise AuthDenied('This account cannot sign in.')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    assignments = serializers.SerializerMethodField()
    lrn = serializers.SerializerMethodField()
    current_school_year = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'approval_status',
            'account_status',
            'lrn',
            'current_school_year',
            'assignments',
        )

    def get_current_school_year(self, user):
        from apps.school.models import SchoolYear

        year = SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()
        if year is None:
            return None
        return {'id': year.id, 'label': year.label}

    def get_lrn(self, user):
        profile = getattr(user, 'student_profile', None)
        return profile.lrn if profile else ''

    def get_assignments(self, user):
        if user.role != User.Role.TEACHER:
            return []
        from apps.school.labels import section_label

        rows = user.teaching_assignments.filter(status='active').select_related(
            'subject', 'section', 'section__program', 'school_year'
        )
        return [
            {
                'id': row.id,
                'type': row.assignment_type,
                'school_year': row.school_year.label,
                'grade_level': row.grade_level,
                'section': section_label(row.section) if row.section_id else None,
                'subject': row.subject.name if row.subject else None,
            }
            for row in rows
        ]


class ActivateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs['email'].strip()).first()
        if user is None:
            raise serializers.ValidationError({'email': 'No account matches that email.'})
        if user.account_status == User.AccountStatus.ACTIVE and user.has_usable_password():
            raise serializers.ValidationError({'email': 'This account is already activated.'})
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        if not consume_code(user, 'activate', attrs['code']):
            raise serializers.ValidationError({'code': 'That code is invalid or has expired.'})
        attrs['user'] = user
        return attrs


class PasswordOtpSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if not user.email:
            raise serializers.ValidationError({'current_password': 'This account has no email for a code.'})
        attrs['user'] = user
        return attrs


class PasswordCodeVerifySerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    code = serializers.CharField()

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if not check_code(user, 'password', attrs['code']):
            raise serializers.ValidationError({'code': 'That code is invalid or has expired.'})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        if attrs['new_password'] == attrs['current_password']:
            raise serializers.ValidationError({'new_password': 'Choose a password that is different from the current one.'})
        if not consume_code(user, 'password', attrs['code']):
            raise serializers.ValidationError({'code': 'That code is invalid or has expired.'})
        return attrs


class ForgotPasswordOtpSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    recaptcha_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        verify_recaptcha(attrs.pop('recaptcha_token', ''))
        user = find_portal_user(attrs['identifier'])
        attrs['user'] = user if user and user.email and user.has_usable_password() else None
        return attrs


class ForgotPasswordVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField()
    recaptcha_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        verify_recaptcha(attrs.pop('recaptcha_token', ''))
        user = find_portal_user(attrs['identifier'])
        if user is None or not user.has_usable_password() or not check_code(user, 'password', attrs['code']):
            raise serializers.ValidationError({'code': 'That code is invalid or has expired.'})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    recaptcha_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        verify_recaptcha(attrs.pop('recaptcha_token', ''))
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        user = find_portal_user(attrs['identifier'])
        if user is None or not user.has_usable_password() or not consume_code(user, 'password', attrs['code']):
            raise serializers.ValidationError({'code': 'That code is invalid or has expired.'})
        attrs['user'] = user
        return attrs


def send_password_otp(user):
    """Email a fresh password code, at most one per resend window so an inbox cannot be flooded."""
    wait = resend_wait(user, 'password')
    if wait:
        raise CodeCooldown(f'Please wait {wait} seconds before asking for a new code.')
    password_otp_email(user, issue_code(user, 'password', minutes=10))
