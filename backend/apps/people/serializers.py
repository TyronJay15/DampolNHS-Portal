from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import StudentProfile, User
from apps.accounts.passwords import validate_password_strength
from apps.accounts.recaptcha import verify_recaptcha
from apps.people.models import Registration
from apps.school.curriculum import programs_for
from apps.school.models import Program, SchoolYear
from apps.school.program_catalog import grade_for


def digits_only(value, field_name):
    text = str(value).strip()
    if not text.isdigit():
        raise serializers.ValidationError({field_name: 'Use numbers only.'})
    return text


class StudentRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100)
    lrn = serializers.CharField(max_length=32)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    contact_number = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    birthdate = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=StudentProfile.Gender.choices)
    guardian_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    guardian_contact = serializers.CharField(max_length=20, required=False, allow_blank=True)
    previous_school = serializers.CharField(max_length=255, required=False, allow_blank=True)
    grade_level_current = serializers.CharField(max_length=32, required=False, allow_blank=True)
    grade_level_enrollment = serializers.CharField(max_length=32)
    program = serializers.CharField()
    school_year = serializers.CharField(required=False, allow_blank=True)
    recaptcha_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_lrn(self, value):
        cleaned = value.strip()
        if not all(ch.isdigit() or ch == '-' for ch in cleaned):
            raise serializers.ValidationError('LRN may contain numbers and hyphens only.')
        if len(''.join(ch for ch in cleaned if ch.isdigit())) != 12:
            raise serializers.ValidationError('LRN must be 12 digits.')
        if StudentProfile.objects.filter(lrn__iexact=cleaned).exists():
            raise serializers.ValidationError('An account with this LRN already exists.')
        return cleaned

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate_address(self, value):
        cleaned = value.strip()
        if len(cleaned) < 10 or len(cleaned) > 255:
            raise serializers.ValidationError('Address must be 10 to 255 characters.')
        return cleaned

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate_contact_number(self, value):
        digits = digits_only(value, 'contact_number')
        if not digits.startswith('09') or len(digits) != 11:
            raise serializers.ValidationError('Contact number must be 11 digits starting with 09.')
        return digits

    def validate_guardian_contact(self, value):
        if not value:
            return ''
        return digits_only(value, 'guardian_contact')

    def validate_program(self, value):
        code = value.strip().upper()
        program = Program.objects.filter(code=code, is_active=True).first()
        if not program:
            raise serializers.ValidationError('Select a valid program.')
        return program

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        year_label = attrs.get('school_year')
        year = (
            SchoolYear.objects.filter(label=year_label).first()
            if year_label
            else SchoolYear.objects.filter(is_current=True).first()
        )
        if not year:
            raise ValidationError({'school_year': 'No school year is available for registration.'})
        verify_recaptcha(attrs.pop('recaptcha_token', ''))
        program = attrs['program']
        chosen = (attrs.get('grade_level_enrollment') or '').strip()
        required = program.grade_level or grade_for(program.code)
        if required and chosen and chosen != required:
            raise ValidationError({'program': f'{program.code} is a {required} program, not a {chosen} program.'})
        grade = required or chosen
        if program.grade_level and not programs_for(year, grade).filter(pk=program.pk).exists():
            raise ValidationError({'program': f'{program.code} is not offered for {grade} in {year.label}.'})
        attrs['grade_level_enrollment'] = grade
        attrs['school_year'] = year
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        program = validated_data['program']
        school_year = validated_data['school_year']
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')
        validated_data.pop('school_year')
        validated_data.pop('program')

        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.PENDING,
            account_status=User.AccountStatus.ACTIVE,
        )
        StudentProfile.objects.create(
            user=user,
            lrn=validated_data['lrn'],
            middle_name=validated_data.get('middle_name', ''),
            contact_number=validated_data['contact_number'],
            address=validated_data['address'],
            birthdate=validated_data.get('birthdate'),
            gender=validated_data['gender'],
            guardian_name=validated_data.get('guardian_name', ''),
            guardian_contact=validated_data.get('guardian_contact', ''),
            grade_level=validated_data['grade_level_enrollment'],
        )
        Registration.objects.create(
            user=user,
            school_year=school_year,
            program=program,
            previous_school=validated_data.get('previous_school', ''),
            grade_level_current=validated_data.get('grade_level_current', ''),
            grade_level_enrollment=validated_data['grade_level_enrollment'],
            status=Registration.Status.PENDING,
        )
        return user


class RegistrationReviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    approval_status = serializers.CharField(source='user.approval_status', read_only=True)
    account_status = serializers.CharField(source='user.account_status', read_only=True)
    lrn = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    contact_number = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    guardian_contact = serializers.SerializerMethodField()
    program_code = serializers.CharField(source='program.code', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    school_year = serializers.CharField(source='school_year.label', read_only=True)
    reviewed_by_email = serializers.SerializerMethodField()
    email_delivery = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = (
            'id',
            'user_id',
            'email',
            'first_name',
            'last_name',
            'lrn',
            'gender',
            'contact_number',
            'address',
            'guardian_name',
            'guardian_contact',
            'program_code',
            'program_name',
            'school_year',
            'grade_level_enrollment',
            'status',
            'approval_status',
            'account_status',
            'rejection_reason',
            'submitted_at',
            'reviewed_at',
            'reviewed_by_email',
            'email_delivery',
        )

    def _profile(self, row):
        return getattr(row.user, 'student_profile', None)

    def get_lrn(self, row):
        profile = self._profile(row)
        return profile.lrn if profile else ''

    def get_gender(self, row):
        profile = self._profile(row)
        return profile.gender if profile else ''

    def get_contact_number(self, row):
        profile = self._profile(row)
        return profile.contact_number if profile else ''

    def get_address(self, row):
        profile = self._profile(row)
        return profile.address if profile else ''

    def get_guardian_name(self, row):
        profile = self._profile(row)
        return profile.guardian_name if profile else ''

    def get_guardian_contact(self, row):
        profile = self._profile(row)
        return profile.guardian_contact if profile else ''

    def get_reviewed_by_email(self, row):
        return row.reviewed_by.email if row.reviewed_by_id else ''

    def get_email_delivery(self, row):
        """The result email's state, given by the Admin's list view. None when there is none to show."""
        return self.context.get('email_states', {}).get(row.id)


class StudentProfileUpdateSerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    gender = serializers.ChoiceField(choices=StudentProfile.Gender.choices)
    guardian_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    guardian_contact = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_contact_number(self, value):
        digits = digits_only(value, 'contact_number')
        if not digits.startswith('09') or len(digits) != 11:
            raise serializers.ValidationError('Contact number must be 11 digits starting with 09.')
        return digits

    def validate_address(self, value):
        cleaned = value.strip()
        if len(cleaned) < 10 or len(cleaned) > 255:
            raise serializers.ValidationError('Address must be 10 to 255 characters.')
        return cleaned

    def validate_guardian_name(self, value):
        return value.strip()

    def validate_guardian_contact(self, value):
        if not value:
            return ''
        return digits_only(value, 'guardian_contact')


class StudentGenderSerializer(serializers.Serializer):
    """The admin's correction of a student's gender, e.g. before a DepEd report."""

    gender = serializers.ChoiceField(choices=StudentProfile.Gender.choices)


class RejectRegistrationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)

    def validate_reason(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('A rejection reason is required.')
        return cleaned


class StaffCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=(
            (User.Role.TEACHER, 'Teacher'),
            (User.Role.HEAD_TEACHER, 'Head teacher'),
        )
    )

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email


    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=None,
            first_name=validated_data['first_name'].strip(),
            last_name=validated_data['last_name'].strip(),
            role=validated_data['role'],
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.PENDING_ACTIVATION,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user
