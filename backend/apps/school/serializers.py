import re

from rest_framework import serializers

from apps.school.curriculum import GRADE_LEVELS, curriculum_for, set_year_curricula
from apps.school.models import Curriculum, Program, ProgramSubject, SchoolYear, Section, SkillDomain, Subject, Term
from apps.school.offerings import replace_program_subjects, subject_payloads_for_program
from apps.school.program_catalog import extra_for, grade_for
from apps.school.term_plan import clean_terms

CODE_RE = re.compile(r'^[A-Z0-9]{2,16}$')


class ProgramSerializer(serializers.ModelSerializer):
    track = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    pathways = serializers.SerializerMethodField()
    grade_level = serializers.SerializerMethodField()
    curriculum = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = (
            'id',
            'code',
            'name',
            'summary',
            'description',
            'is_active',
            'sort_order',
            'track',
            'subjects',
            'pathways',
            'grade_level',
            'curriculum',
        )

    def get_track(self, obj):
        return obj.track or extra_for(obj.code).get('track', '')

    def get_subjects(self, obj):
        """Public subject list. Default terms are internal planning data, so they are left out."""
        rows = subject_payloads_for_program(obj)
        if rows:
            return [{key: value for key, value in row.items() if key != 'terms'} for row in rows]
        return [{'id': None, 'code': '', 'name': name, 'kind': ''} for name in extra_for(obj.code).get('subjects', [])]

    def get_pathways(self, obj):
        return obj.pathways or extra_for(obj.code).get('pathways', [])

    def get_grade_level(self, obj):
        return obj.grade_level or grade_for(obj.code)

    def get_curriculum(self, obj):
        return obj.curriculum.name if obj.curriculum_id else ''


class AdminProgramSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    curriculum = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Curriculum.objects.all(),
        allow_null=True,
        required=False,
    )
    continues_to = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Program
        fields = (
            'id',
            'code',
            'name',
            'summary',
            'description',
            'track',
            'grade_level',
            'pathways',
            'curriculum',
            'continues_to',
            'is_active',
            'sort_order',
            'subjects',
        )

    def validate_code(self, value):
        code = str(value or '').strip().upper()
        if not CODE_RE.match(code):
            raise serializers.ValidationError('Use 2–16 letters or numbers.')
        if self.instance is None and Program.objects.filter(code=code).exists():
            raise serializers.ValidationError('That program code already exists.')
        return code

    def validate_grade_level(self, value):
        if value not in dict(Program.GradeLevel.choices):
            raise serializers.ValidationError('Choose Grade 11 or Grade 12.')
        return value

    def validate_pathways(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('pathways must be a list.')
        return [str(item).strip() for item in value if str(item).strip()]

    def get_subjects(self, obj):
        return subject_payloads_for_program(obj)

    def validate(self, attrs):
        if self.instance is None and not attrs.get('grade_level'):
            raise serializers.ValidationError({'grade_level': 'Choose Grade 11 or Grade 12.'})
        target = attrs.get('continues_to')
        if target is not None:
            if self.instance is not None and target.pk == self.instance.pk:
                raise serializers.ValidationError({'continues_to': 'A program cannot continue to itself.'})
            if target.grade_level != Program.GradeLevel.GRADE_12:
                raise serializers.ValidationError({'continues_to': 'Choose a Grade 12 program.'})
        if 'subjects' in self.initial_data:
            attrs['subjects'] = self._clean_subjects(self.initial_data.get('subjects'))
        return attrs

    def _clean_subjects(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError({'subjects': 'subjects must be a list.'})
        cleaned = []
        seen = set()
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError({'subjects': 'Each row needs a subject.'})
            subject_id = item.get('subject_id') or item.get('id')
            try:
                subject_id = int(subject_id)
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError({'subjects': 'Each row needs a subject.'}) from exc
            kind = item.get('kind') or ProgramSubject.Kind.CORE
            if kind not in ProgramSubject.Kind.values:
                raise serializers.ValidationError({'subjects': 'Choose core, elective, applied, or specialized.'})
            try:
                terms = clean_terms(item.get('terms') or [])
            except ValueError as exc:
                raise serializers.ValidationError({'subjects': 'Default terms must be 1, 2, or 3.'}) from exc
            if subject_id in seen:
                raise serializers.ValidationError({'subjects': 'A subject can only appear once.'})
            seen.add(subject_id)
            cleaned.append({'subject_id': subject_id, 'kind': kind, 'terms': terms})
        found = set(Subject.objects.filter(id__in=seen, is_active=True).values_list('id', flat=True))
        if seen - found:
            raise serializers.ValidationError({'subjects': 'One or more subjects are not in the catalog.'})
        return cleaned

    def create(self, validated_data):
        subjects = validated_data.pop('subjects', None)
        program = Program.objects.create(**validated_data)
        if subjects is not None:
            replace_program_subjects(program, subjects)
        return program

    def update(self, instance, validated_data):
        subjects = validated_data.pop('subjects', None)
        validated_data.pop('code', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if subjects is not None:
            replace_program_subjects(instance, subjects)
        return instance


class SchoolYearSerializer(serializers.ModelSerializer):
    archived = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    curricula = serializers.SerializerMethodField()
    curriculum_options = serializers.SerializerMethodField()

    class Meta:
        model = SchoolYear
        fields = (
            'id',
            'label',
            'is_current',
            'starts_on',
            'ends_on',
            'archived_at',
            'archived',
            'can_delete',
            'curricula',
            'curriculum_options',
        )
        extra_kwargs = {'archived_at': {'read_only': True}}

    def get_curricula(self, obj):
        rows = {}
        for grade_level in GRADE_LEVELS:
            curriculum = curriculum_for(obj, grade_level)
            rows[grade_level] = curriculum.code if curriculum else ''
        return rows

    def get_curriculum_options(self, obj):
        return list(Curriculum.objects.filter(is_active=True).values('code', 'name'))

    def validate(self, attrs):
        if 'curricula' in self.initial_data:
            attrs['curricula'] = self._clean_curricula(self.initial_data.get('curricula'))
        return attrs

    def _clean_curricula(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError({'curricula': 'Send a curriculum per grade level.'})
        by_code = {row.code: row for row in Curriculum.objects.filter(is_active=True)}
        cleaned = {}
        for grade_level, code in value.items():
            if grade_level not in GRADE_LEVELS or code not in by_code:
                raise serializers.ValidationError({'curricula': 'Choose a listed curriculum for Grade 11 or Grade 12.'})
            cleaned[grade_level] = by_code[code]
        return cleaned

    def create(self, validated_data):
        curricula = validated_data.pop('curricula', None)
        year = super().create(validated_data)
        if curricula:
            set_year_curricula(year, curricula)
        return year

    def update(self, instance, validated_data):
        curricula = validated_data.pop('curricula', None)
        year = super().update(instance, validated_data)
        if curricula:
            set_year_curricula(year, curricula)
        return year

    def get_archived(self, obj):
        return bool(obj.archived_at)

    def get_can_delete(self, obj):
        if obj.is_current or obj.archived_at:
            return False
        return not obj.sections.exists()

    def validate_label(self, value):
        label = str(value or '').strip()
        if not re.match(r'^\d{4}-\d{4}$', label):
            raise serializers.ValidationError('Use YYYY-YYYY, for example 2025-2026.')
        return label


class TermSerializer(serializers.ModelSerializer):
    school_year_label = serializers.CharField(source='school_year.label', read_only=True)
    encode_open = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = (
            'id',
            'school_year',
            'school_year_label',
            'number',
            'label',
            'status',
            'is_current',
            'start_date',
            'end_date',
            'encode_opens_at',
            'encode_closes_at',
            'encode_open',
        )
        extra_kwargs = {
            'school_year': {'read_only': True},
            'number': {'read_only': True},
            'label': {'read_only': True},
            'status': {'read_only': True},
            'is_current': {'read_only': True},
            'start_date': {'read_only': True},
            'end_date': {'read_only': True},
        }

    def get_encode_open(self, obj):
        from apps.school.deadlines import encode_is_open

        return encode_is_open(obj)

    def validate(self, attrs):
        opens = attrs.get('encode_opens_at', getattr(self.instance, 'encode_opens_at', None))
        closes = attrs.get('encode_closes_at', getattr(self.instance, 'encode_closes_at', None))
        if opens and closes and closes <= opens:
            raise serializers.ValidationError({'encode_closes_at': 'Close time must be after the open time.'})
        return attrs


class SubjectSerializer(serializers.ModelSerializer):
    skill_domain = serializers.SlugRelatedField(
        slug_field='key',
        queryset=SkillDomain.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Subject
        fields = ('id', 'code', 'name', 'skill_domain', 'is_active')


class SectionSerializer(serializers.ModelSerializer):
    school_year_label = serializers.CharField(source='school_year.label', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    display_label = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    archived = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    identity_locked = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = (
            'id',
            'name',
            'display_label',
            'grade_level',
            'capacity',
            'status',
            'is_active',
            'school_year',
            'school_year_label',
            'program',
            'program_code',
            'program_name',
            'student_count',
            'progress_percent',
            'identity_locked',
            'can_delete',
            'archived_at',
            'archived',
        )
        extra_kwargs = {'archived_at': {'read_only': True}}

    def get_display_label(self, obj):
        from apps.school.labels import section_label

        return section_label(obj)

    def get_student_count(self, obj):
        return obj.student_assignments.filter(is_active=True).count()

    def get_can_delete(self, obj):
        if obj.student_assignments.exists() or obj.teacher_assignments.exists():
            return False
        from apps.grading.models import Grade

        return not Grade.objects.filter(section=obj).exists()

    def get_archived(self, obj):
        return bool(obj.archived_at)

    def get_progress_percent(self, obj):
        from apps.school.section_progress import section_progress

        return section_progress(obj)['progress_percent']

    def get_identity_locked(self, obj):
        from apps.school.models import Section

        return obj.status == Section.Status.ACTIVE or bool(obj.archived_at)

    def validate_capacity(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('Capacity must be at least 1.')
        if value is not None and value > 999:
            raise serializers.ValidationError('Capacity is too large.')
        return value

    def validate(self, attrs):
        program = attrs.get('program', getattr(self.instance, 'program', None))
        grade_level = attrs.get('grade_level', getattr(self.instance, 'grade_level', None))
        if not program:
            raise serializers.ValidationError({'program': 'Choose a program.'})
        required = grade_for(program.code)
        if required and grade_level and required != grade_level:
            raise serializers.ValidationError({'program': f'{program.code} is a {required} program.'})
        instance = self.instance
        if instance and (instance.status == Section.Status.ACTIVE or instance.archived_at):
            for field in ('school_year', 'grade_level', 'program', 'name'):
                if field not in attrs:
                    continue
                if attrs[field] != getattr(instance, field):
                    raise serializers.ValidationError(
                        {
                            'detail': (
                                'Section identity is locked while active. '
                                'Archive and create a new section instead.'
                            )
                        }
                    )
        return attrs
