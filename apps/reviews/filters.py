import django_filters as filters

from .models import Review


class ReviewFilter(filters.FilterSet):
    rating = filters.NumberFilter(field_name="rating", lookup_expr="exact")
    reviewer = filters.UUIDFilter(field_name="reviewer_id")
    reviewee = filters.UUIDFilter(field_name="reviewee_id")
    job = filters.UUIDFilter(field_name="job_id")
    service = filters.UUIDFilter(field_name="service_id")

    class Meta:
        model = Review
        fields = ["rating", "reviewer", "reviewee", "job", "service"]
