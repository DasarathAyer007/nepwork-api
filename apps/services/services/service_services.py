# services/query_service.py

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import F, Q, QuerySet
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..models import Service
from ..selectors import services_selectors as selectors


class ServiceQueryService:
    ALLOWED_ORDERINGS = {
        "price",
        "-price",
        "created_at",
        "-created_at",
        "available_from",
        "-available_from",
        "total_applies",
        "-total_applies",
        "distance",
    }
    DEFAULT_ORDERING = "-created_at"

    def __init__(self, user=None, params: dict | None = None):
        self.user = user
        self.params = params or {}

    def list_services(self) -> QuerySet:
        qs = selectors.get_active_services(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo_if_provided(qs)

    def near_me(self) -> QuerySet:
        self._validate_geo_params(required=True)
        qs = selectors.get_active_services(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo(qs)

    def trending(self) -> QuerySet:
        qs = selectors.get_trending_services(self.user)
        qs = self._apply_filters(qs, skip_ordering=True)
        return self._apply_geo_if_provided(qs)

    def recommendations(self) -> QuerySet:
        if not self.user or not self.user.is_authenticated:
            raise ValidationError("Authentication required.")
        qs = selectors.get_recommendation_queryset(self.user)
        qs = self._apply_filters(qs, skip_ordering=True)
        return self._apply_geo_if_provided(qs)

    def saved(self) -> QuerySet:
        if not self.user or not self.user.is_authenticated:
            raise ValidationError("Authentication required.")
        qs = selectors.get_saved_services(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo_if_provided(qs)

    def my_services(self) -> QuerySet:
        if not self.user or not self.user.is_authenticated:
            raise ValidationError("Authentication required.")
        qs = selectors.get_my_services(self.user)
        return self._apply_my_service_filters(qs)

    def similar(self, service_id) -> QuerySet:
        service = selectors.get_service_by_id(service_id)
        qs = selectors.get_similar_services(service, self.user)
        return self._apply_filters(qs, skip_status=True)

    # Core filter pipeline
    def _apply_filters(self, qs, skip_ordering=False, skip_status=False):
        qs = self._filter_price(qs)
        if not skip_status:
            qs = self._filter_status(qs)
        qs = self._filter_category(qs)
        qs = self._filter_skills(qs)
        qs = self._filter_location_text(qs)
        qs = self._filter_radius(qs)
        qs = self._filter_time(qs)
        qs = self._filter_availability(qs)
        qs = self._filter_search(qs)
        qs = self._filter_has_location(qs)
        if not skip_ordering:
            qs = self._apply_ordering(qs)
        return qs

    def _apply_my_service_filters(self, qs):
        qs = self._filter_price(qs)
        qs = self._filter_category(qs)
        qs = self._filter_skills(qs)
        qs = self._filter_search(qs)
        if status := self.params.get("status"):
            qs = qs.filter(status=status)
        return self._apply_ordering(qs)

    # Individual filter methods
    def _filter_price(self, qs):
        if price_min := self.params.get("price_min"):
            qs = qs.filter(price__gte=price_min)
        if price_max := self.params.get("price_max"):
            qs = qs.filter(price__lte=price_max)
        if currency := self.params.get("currency"):
            qs = qs.filter(currency__iexact=currency)
        if price_type := self.params.get("price_type"):
            qs = qs.filter(price_type=price_type)
        return qs

    def _filter_status(self, qs):
        avail = self.params.get("availability_status")
        if avail:
            values = avail if isinstance(avail, list) else [avail]
            qs = qs.filter(availability_status__in=values)
        return qs

    def _filter_category(self, qs):
        if cat_id := self.params.get("category"):
            qs = qs.filter(category__id=cat_id)
        if cat_slug := self.params.get("category_slug"):
            qs = qs.filter(category__slug__iexact=cat_slug)
        return qs

    def _filter_skills(self, qs):
        skills = self.params.get("skills")
        if skills:
            skill_list = skills if isinstance(skills, list) else [skills]
            qs = qs.filter(skills__id__in=skill_list).distinct()
        return qs

    def _filter_location_text(self, qs):
        for field in ("city", "state", "country", "postal_code"):
            val = self.params.get(field)
            if val:
                qs = qs.filter(**{f"location__{field}__icontains": val})
        return qs

    def _filter_radius(self, qs):
        if r_min := self.params.get("radius_min"):
            qs = qs.filter(radius_km__gte=r_min)
        if r_max := self.params.get("radius_max"):
            qs = qs.filter(radius_km__lte=r_max)
        return qs

    def _filter_time(self, qs):
        if available_from := self.params.get("available_from"):
            qs = qs.filter(available_from__gte=available_from)
        if available_to := self.params.get("available_to"):
            qs = qs.filter(available_to__lte=available_to)
        return qs

    def _filter_availability(self, qs):
        if not self.params.get("is_available"):
            return qs
        now = timezone.now().time()
        return qs.filter(
            availability_status=Service.AvailabilityStatus.AVAILABLE
        ).filter(
            Q(available_from__lte=now, available_to__gte=now)
            | Q(available_from__gt=F("available_to"))
        )

    def _filter_search(self, qs):
        search = self.params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return qs

    def _filter_has_location(self, qs):
        val = self.params.get("has_location")
        if val is None:
            return qs
        if str(val).lower() in ("true", "1"):
            return qs.filter(location__isnull=False)
        return qs.filter(location__isnull=True)

    def _apply_ordering(self, qs):
        ordering = self.params.get("ordering", self.DEFAULT_ORDERING)
        if ordering not in self.ALLOWED_ORDERINGS:
            ordering = self.DEFAULT_ORDERING
        if ordering == "distance" and not self._has_geo_params():
            ordering = self.DEFAULT_ORDERING
        return qs.order_by(ordering)

    #  Geo helpers for location filter
    def _apply_geo(self, qs):
        lat = float(self.params["lat"])
        lng = float(self.params["lng"])
        radius_km = float(self.params.get("radius_km", 10))
        point = Point(lng, lat, srid=4326)
        return (
            qs.filter(location__point__dwithin=(point, D(km=radius_km)))
            .annotate(distance=Distance("location__point", point))
            .order_by("distance")
        )

    def _apply_geo_if_provided(self, qs):
        if self._has_geo_params():
            self._validate_geo_params(required=False)
            return self._apply_geo(qs)
        return qs

    def _has_geo_params(self):
        return bool(self.params.get("lat") and self.params.get("lng"))

    def _validate_geo_params(self, required=False):
        lat = self.params.get("lat")
        lng = self.params.get("lng")
        if required and (not lat or not lng):
            raise ValidationError({"detail": "lat and lng are required."})
        if lat and not lng:
            raise ValidationError({"lng": "Required with lat."})
        if lng and not lat:
            raise ValidationError({"lat": "Required with lng."})
        if lat:
            try:
                f = float(lat)
                if not -90 <= f <= 90:
                    raise ValidationError({"lat": "Must be -90..90"})
            except (TypeError, ValueError):
                raise ValidationError({"lat": "Invalid number"})
        if lng:
            try:
                f = float(lng)
                if not -180 <= f <= 180:
                    raise ValidationError({"lng": "Must be -180..180"})
            except (TypeError, ValueError):
                raise ValidationError({"lng": "Invalid number"})
