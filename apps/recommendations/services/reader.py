from django.db.models import Case, QuerySet, When

from .cache import RecommendationCache
from .engine import RecommendationEngine


class RecommendationReadService:
    """
    Cache-or-generate + preserved-order reordering. Contains no Job/Service
    specific filtering logic — callers pass their own base queryset (e.g.
    the existing `get_active_jobs`/`get_active_services` selectors) so this
    stays reusable across domains.
    """

    def __init__(
        self,
        cache: RecommendationCache | None = None,
        engine: RecommendationEngine | None = None,
    ):
        self.cache = cache or RecommendationCache()
        self.engine = engine or RecommendationEngine()

    def get_ranked_ids(
        self, user_id, feed_type: str, top_n: int = 20
    ) -> list[str]:
        cached = self.cache.get(user_id, feed_type)
        if cached is not None:
            return [item["id"] for item in cached[:top_n]]

        result = self.engine.generate_for_user(
            user_id, top_n=top_n
        )  # also caches internally
        return [item["id"] for item in result[feed_type][:top_n]]

    @staticmethod
    def reorder_queryset(
        queryset: QuerySet, ordered_ids: list[str], pk_field: str = "id"
    ) -> QuerySet:
        """Case/When preserved-order technique"""
        if not ordered_ids:
            return queryset.none()
        preserved = Case(
            *[
                When(**{pk_field: pk}, then=pos)
                for pos, pk in enumerate(ordered_ids)
            ]
        )
        return queryset.filter(**{f"{pk_field}__in": ordered_ids}).order_by(
            preserved
        )
