from django.db.models import QuerySet

from ..models import ServiceRequest


def get_service_requests_base(user=None) -> QuerySet:
    """Base queryset with related data."""
    return ServiceRequest.objects.select_related("service", "user", "location")
