from django.db.models import QuerySet

from ..models import JobApplication


def get_applications_base(user=None) -> QuerySet:
    return JobApplication.objects.filter(
        deleted_at__isnull=True
    ).select_related("job", "applicant", "reviewed_by")
