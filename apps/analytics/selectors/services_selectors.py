from apps.services.models import Service
from apps.services.selectors.request_selectors import (
    get_service_requests_base,
)


def get_services_for_analytics(category=None):
    """A plain, unannotated queryset of every non-deleted service.
    Deliberately NOT apps.services.selectors.services_selectors.
    get_base_service_queryset — that selector's own
    total_applies=Count("service_requests") annotation causes a JOIN
    fan-out when combined with a further .values().annotate(Count("id")),
    silently overcounting any service with more than one request."""
    qs = Service.objects.filter(deleted_at__isnull=True)
    if category:
        qs = qs.filter(category_id=category)
    return qs


def get_service_requests_for_analytics(category=None):
    qs = get_service_requests_base().filter(deleted_at__isnull=True)
    if category:
        qs = qs.filter(service__category_id=category)
    return qs
