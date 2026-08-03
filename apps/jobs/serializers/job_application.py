from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.jobs.models.jobs import Job
from apps.utils.html_sanitizer import clean_and_validate_rich_text

from ..models import JobApplication
from ..services.job_application import ApplicationTransitionService

User = get_user_model()

RESUME_MAX_SIZE = 10 * 1024 * 1024  # 10MB
RESUME_ALLOWED_CONTENT_TYPES = [
    "application/pdf",
]


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
    applicant = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    status = serializers.ChoiceField(
        choices=JobApplication.ApplicationStatus.choices, required=False
    )

    class Meta:
        model = JobApplication
        fields = [
            "job",
            "applicant",
            "resume",
            "cover_letter",
            "status",
            "expected_salary",
            "years_of_experience",
            "notes",
        ]

    def validate_job(self, value):
        user = self.context["request"].user
        if user.account_type != "admin":
            if value.status != Job.JobStatus.OPEN:
                raise serializers.ValidationError(
                    "Job is not open for applications."
                )
            if value.posted_by == user:
                raise serializers.ValidationError(
                    "Cannot apply to your own job."
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
        user = self.context["request"].user
        if user.account_type == "admin":
            return value or ""
        return clean_and_validate_rich_text(
            value, min_length=50, max_length=None
        )

    def validate(self, attrs):
        user = self.context["request"].user

        applicant = attrs.get("applicant")
        if self.instance is None:
            if applicant is None:
                if user.account_type != "admin":
                    applicant = user
                    attrs["applicant"] = user
                else:
                    raise serializers.ValidationError(
                        {"applicant": "Applicant is required for admins."}
                    )
        else:
            applicant = attrs.get("applicant", self.instance.applicant)

        job = attrs.get("job", self.instance.job if self.instance else None)

        if job and applicant:
            existing = JobApplication.objects.filter(
                job=job, applicant=applicant, deleted_at__isnull=True
            ).exclude(
                status__in=[
                    JobApplication.ApplicationStatus.WITHDRAWN,
                    JobApplication.ApplicationStatus.REJECTED,
                ]
            )
            if self.instance is not None:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": "An active application already exists for this applicant and job."
                    }
                )

        if (
            "status" in attrs
            and attrs["status"] != JobApplication.ApplicationStatus.APPLIED
        ) and user.account_type != "admin":
            raise serializers.ValidationError(
                {"status": "Only admins can set a custom status."}
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if user.account_type == "admin":
            validated_data["reviewed_by"] = user
        try:
            return JobApplication.objects.create(**validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {
                    "job": "An active application already exists for this applicant and job."
                }
            ) from exc

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if user.account_type == "admin":
            validated_data["reviewed_by"] = user
        return super().update(instance, validated_data)


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
