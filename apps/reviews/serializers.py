from __future__ import annotations

from rest_framework import serializers

from apps.users.models import User

from .models import Review


class ReviewUserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name"]
        read_only_fields = fields


class ReviewTargetMixin:
    def get_target_type(self, obj: Review) -> str:
        return "job" if obj.job_id else "service"

    def get_target_id(self, obj: Review):
        return obj.job_id or obj.service_id


class ReviewListSerializer(ReviewTargetMixin, serializers.ModelSerializer):
    reviewer = ReviewUserBriefSerializer(read_only=True)
    reviewee = ReviewUserBriefSerializer(read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer",
            "reviewee",
            "target_type",
            "target_id",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReviewDetailSerializer(ReviewTargetMixin, serializers.ModelSerializer):
    reviewer = ReviewUserBriefSerializer(read_only=True)
    reviewee = ReviewUserBriefSerializer(read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer",
            "reviewee",
            "target_type",
            "target_id",
            "target",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_target(self, obj: Review) -> dict:
        if obj.job_id:
            return {"id": obj.job_id, "title": obj.job.title}
        return {"id": obj.service_id, "title": obj.service.title}


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_comment(self, value: str) -> str:
        return value.strip()


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "comment"]

    def validate_comment(self, value: str) -> str:
        return value.strip()
