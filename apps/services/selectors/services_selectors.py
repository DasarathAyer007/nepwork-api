from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
    QuerySet,
)

from ..models import Service, ServiceRequest, ServiceSaved


def get_base_service_queryset(user=None) -> QuerySet:
    """
    Annotated base queryset shared by all selectors.
    Annotations: avg_rating, total_applies (from ServiceRequest),
    is_saved (via ServiceSaved), has_applied (via ServiceRequest).
    """
    qs = (
        Service.objects.filter(deleted_at__isnull=True)
        .select_related("user", "category", "location")
        .prefetch_related("skills")
        .annotate(
            # avg_rating=Avg("reviews__rating"),  # adjust related_name if needed
            total_applies=Count("service_requests"),  # using ServiceRequest
        )
    )

    if user and user.is_authenticated:
        saved_sub = ServiceSaved.objects.filter(
            user=user, service=OuterRef("pk")
        )

        applied_sub = ServiceRequest.objects.filter(
            user=user, service=OuterRef("pk")
        )

        qs = qs.annotate(
            is_saved=Exists(saved_sub),
            has_applied=Exists(applied_sub),
        )
    return qs


def get_active_services(user=None) -> QuerySet:
    return get_base_service_queryset(user).filter(
        status=Service.ServiceStatus.ACTIVE
    )


def get_service_by_id(service_id, user=None) -> Service:
    return get_base_service_queryset(user).get(pk=service_id)


def get_my_services(user) -> QuerySet:
    return get_base_service_queryset().filter(user=user)


def get_saved_services(user) -> QuerySet:
    """Services the user has saved (bookmarked)."""
    saved_ids = ServiceSaved.objects.filter(user=user).values("service_id")
    return get_active_services(user).filter(id__in=saved_ids)


def get_trending_services(user=None, days=7) -> QuerySet:
    """
    Not implmented
    """
    return get_active_services(user).order_by("-total_applies", "-created_at")


def get_similar_services(service, user=None) -> QuerySet:
    """Services sharing the same category or skills. For now"""
    return (
        get_active_services(user)
        .filter(
            Q(category=service.category) | Q(skills__in=service.skills.all())
        )
        .exclude(pk=service.pk)
        .distinct()
    )
