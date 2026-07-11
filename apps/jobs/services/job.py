# jobs/query_service.py
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError

from ..selectors import job as selectors


class JobQueryService:
    ALLOWED_ORDERING = {
        "salary_min",
        "-salary_min",
        "salary_max",
        "-salary_max",
        "created_at",
        "-created_at",
        "total_applications",
        "-total_applications",
        "experience_years",
        "-experience_years",
        "distance",
    }
    DEFAULT_ORDERING = "-created_at"

    def __init__(self, user=None, params: dict | None = None):
        self.user = user
        self.params = params or {}

    # ── Public entry points ──────────────────────────────────
    def list_jobs(self) -> QuerySet:
        qs = selectors.get_active_jobs(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo_if_provided(qs)

    def near_me(self) -> QuerySet:
        self._validate_geo_params(required=True)
        qs = selectors.get_active_jobs(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo(qs)

    def trending(self) -> QuerySet:
        qs = selectors.get_trending_jobs(self.user)
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
        qs = selectors.get_saved_jobs(self.user)
        qs = self._apply_filters(qs)
        return self._apply_geo_if_provided(qs)

    def my_jobs(self) -> QuerySet:
        if not self.user or not self.user.is_authenticated:
            raise ValidationError("Authentication required.")
        qs = selectors.get_my_jobs(self.user)
        return self._apply_my_job_filters(qs)

    def similar(self, job_id) -> QuerySet:
        job = selectors.get_job_by_id(job_id)
        qs = selectors.get_similar_jobs(job, self.user)
        return self._apply_filters(qs, skip_status=True)

    # ── Core filter pipeline ─────────────────────────────────
    def _apply_filters(self, qs, skip_ordering=False, skip_status=False):
        qs = self._filter_salary(qs)
        qs = self._filter_job_type(qs)
        qs = self._filter_work_mode(qs)
        qs = self._filter_experience(qs)
        if not skip_status:
            qs = self._filter_status(qs)
        qs = self._filter_category(qs)
        qs = self._filter_skills(qs)
        qs = self._filter_location_text(qs)
        qs = self._filter_deadline(qs)
        qs = self._filter_search(qs)
        qs = self._filter_organization(qs)
        qs = self._filter_has_location(qs)
        if not skip_ordering:
            qs = self._apply_ordering(qs)
        return qs

    def _apply_my_job_filters(self, qs):
        """Filters for the owner's dashboard."""
        qs = self._filter_salary(qs)
        qs = self._filter_job_type(qs)
        qs = self._filter_work_mode(qs)
        qs = self._filter_category(qs)
        qs = self._filter_skills(qs)
        qs = self._filter_search(qs)
        if status := self.params.get("status"):
            qs = qs.filter(status=status)
        return self._apply_ordering(qs)

    # ── Individual filter methods ────────────────────────────
    def _filter_salary(self, qs):
        if sal_min := self.params.get("salary_min"):
            qs = qs.filter(salary_min__gte=sal_min)
        if sal_max := self.params.get("salary_max"):
            qs = qs.filter(salary_max__lte=sal_max)
        if currency := self.params.get("currency"):
            qs = qs.filter(currency__iexact=currency)
        return qs

    def _filter_job_type(self, qs):
        if jt := self.params.get("job_type"):
            qs = qs.filter(job_type=jt)
        return qs

    def _filter_work_mode(self, qs):
        if wm := self.params.get("work_mode"):
            qs = qs.filter(work_mode=wm)
        return qs

    def _filter_experience(self, qs):
        if exp_level := self.params.get("experience_level"):
            qs = qs.filter(experience_level=exp_level)
        if exp_years := self.params.get("experience_years"):
            qs = qs.filter(experience_years__lte=exp_years)  # at most
        return qs

    def _filter_status(self, qs):
        # Public listing: only OPEN
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
            skill_list = [
                skill.strip() for skill in skills.split(",") if skill.strip()
            ]

            qs = qs.filter(skills_required__name__in=skill_list).distinct()

        return qs

    def _filter_location_text(self, qs):
        for field in ("city", "state", "country", "postal_code"):
            val = self.params.get(field)
            if val:
                qs = qs.filter(**{f"location__{field}__icontains": val})
        return qs

    def _filter_deadline(self, qs):
        if deadline_before := self.params.get("deadline_before"):
            qs = qs.filter(deadline__lte=deadline_before)
        if deadline_after := self.params.get("deadline_after"):
            qs = qs.filter(deadline__gte=deadline_after)
        return qs

    def _filter_search(self, qs):
        search = self.params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return qs

    def _filter_organization(self, qs):
        org_id = self.params.get("organization")
        if org_id:
            qs = qs.filter(organization_id=org_id)
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
        if ordering not in self.ALLOWED_ORDERING:
            ordering = self.DEFAULT_ORDERING
        if ordering == "distance" and not self._has_geo_params():
            ordering = self.DEFAULT_ORDERING
        return qs.order_by(ordering)

    # ── Geo helpers ──────────────────────────────────────────
    def _apply_geo(self, qs):
        lat = float(self.params["lat"])
        lng = float(self.params["lng"])
        radius_km = float(
            self.params.get("radius_km", 50)
        )  # default 50km for jobs
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
