from bleach import clean
from bleach.css_sanitizer import CSSSanitizer
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.jobs.models.jobs import Job

from ..models import JobApplication
from ..services.job_application import ApplicationTransitionService

User = get_user_model()

RESUME_MAX_SIZE = 10 * 1024 * 1024  # 10MB
RESUME_ALLOWED_CONTENT_TYPES = [
    "application/pdf",
]

COVER_LETTER_ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "blockquote",
    "a",
]

COVER_LETTER_ALLOWED_ATTRIBUTES = {
    "a": ["href", "rel", "target"],
    "p": ["style"],
    "h1": ["style"],
    "h2": ["style"],
    "h3": ["style"],
}

COVER_LETTER_ALLOWED_STYLES = ["text-align"]

COVER_LETTER_CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=COVER_LETTER_ALLOWED_STYLES
)

COVER_LETTER_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


class JobApplicationJobSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail",
            "status",
            "posted_by",
            "posted_by_name",
        ]

    def get_posted_by_name(self, obj):
        return str(obj.posted_by) if obj.posted_by else None


class JobApplicationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name", "profile_picture"]


class JobApplicationReadSerializer(serializers.ModelSerializer):
    applicant = JobApplicationUserSerializer(read_only=True)
    job = JobApplicationJobSerializer(read_only=True)
    reviewed_by = JobApplicationUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "applicant",
            "resume",
            "cover_letter",
            "status",
            "expected_salary",
            "years_of_experience",
            "reviewed_by",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobApplicationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            "job",
            "resume",
            "cover_letter",
            "expected_salary",
            "years_of_experience",
            "notes",
            "expected_salary",
        ]

    def validate_job(self, value):
        if value.status != Job.JobStatus.OPEN:
            raise serializers.ValidationError(
                "Job is not open for applications."
            )
        user = self.context["request"].user
        if value.posted_by == user:
            raise serializers.ValidationError("Cannot apply to your own job.")

        existing = JobApplication.objects.filter(job=value, applicant=user)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "You have already applied to this job."
            )
        return value

    def validate_resume(self, value):
        if value is None:
            return value
        if value.size is not None and value.size > RESUME_MAX_SIZE:
            raise serializers.ValidationError("Resume must be under 10MB.")
        content_type = getattr(value, "content_type", None)
        if content_type not in RESUME_ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError("Resume must be a PDF file.")
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Resume must be a PDF file.")
        return value

    def validate_cover_letter(self, value):
        cleaned = clean(
            value,
            tags=COVER_LETTER_ALLOWED_TAGS,
            attributes=COVER_LETTER_ALLOWED_ATTRIBUTES,
            protocols=COVER_LETTER_ALLOWED_PROTOCOLS,
            css_sanitizer=COVER_LETTER_CSS_SANITIZER,
            strip=True,
        )

        text_only = clean(cleaned, tags=[], strip=True).strip()
        if len(text_only) < 50:
            raise serializers.ValidationError(
                "Cover letter must be at least 50 characters long."
            )
        return cleaned

    def create(self, validated_data):
        try:
            return JobApplication.objects.create(**validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"job": "You have already applied to this job."}
            ) from exc


class EmptyActionSerializer(serializers.Serializer):
    pass


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ApplicationTransitionService.EMPLOYER_STATUSES
    )
    # Always optional — sending a message to the applicant is never required,
    # only offered as an option for certain statuses (see
    # ApplicationTransitionService.MESSAGE_CAPABLE_STATUSES on the frontend).
    message = serializers.CharField(
        required=False, allow_blank=True, max_length=5000
    )
    send_message = serializers.BooleanField(required=False, default=True)
    send_email = serializers.BooleanField(required=False, default=True)
