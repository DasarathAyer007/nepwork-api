from django.db.models import Count, Q, QuerySet

from ..models import Service, ServiceCategory


def get_categories_with_service_count() -> QuerySet:
    """Active categories annotated with their active-service count."""
    return ServiceCategory.objects.filter(is_active=True).annotate(
        count=Count(
            "services",
            filter=Q(
                services__status=Service.ServiceStatus.ACTIVE,
            ),
            distinct=True,
        )
    )


def get_popular_categories(limit: int) -> QuerySet:
    return (
        get_categories_with_service_count()
        .filter(count__gt=0)
        .order_by("-count", "name")[:limit]
    )
