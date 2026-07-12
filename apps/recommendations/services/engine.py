from django.utils import timezone

from .cache import RecommendationCache
from .candidate import CandidateGenerator
from .scorer import CandidateScorer, UserPreferenceBuilder

ACTIVITY_LOOKBACK_LIMIT = 500  # most recent N events considered per user


class RecommendationEngine:
    """
    Single entry point: RecommendationEngine().generate_for_user(user_id)

      - get user activity
      - build user preference
      - generate candidates
      - score candidates
      - return + cache top recommendations, per feed (jobs/services)
    """

    def __init__(
        self,
        preference_builder=None,
        candidate_generator=None,
        scorer=None,
        cache=None,
    ):
        self.preference_builder = preference_builder or UserPreferenceBuilder()
        self.candidate_generator = candidate_generator or CandidateGenerator()
        self.scorer = scorer or CandidateScorer()
        self.cache = cache or RecommendationCache()

    def generate_for_user(self, user_id, top_n=20) -> dict:
        activities = self._get_recent_activities(user_id)
        if not activities:
            return self._fallback(user_id, top_n)

        preference = self.preference_builder.build(activities, timezone.now())

        jobs = self._generate_feed(
            preference,
            self.candidate_generator.get_job_candidates,
            self.scorer.score_jobs,
            top_n,
        )
        services = self._generate_feed(
            preference,
            self.candidate_generator.get_service_candidates,
            self.scorer.score_services,
            top_n,
        )

        # cold-start fallback per feed, independently — a user might have
        # signal for jobs but none for services yet.
        if not jobs:
            jobs = self._popular_fallback("jobs", top_n)
        if not services:
            services = self._popular_fallback("services", top_n)

        self.cache.set(user_id, "jobs", jobs)
        self.cache.set(user_id, "services", services)
        return {"jobs": jobs, "services": services}

    def _generate_feed(self, preference, get_candidates, score, top_n):
        candidates = get_candidates(preference)
        return score(candidates, preference)[:top_n]

    def _get_recent_activities(self, user_id):
        from apps.user_activity.models import UserActivity

        return list(
            UserActivity.objects.filter(user_id=user_id).order_by(
                "-created_at"
            )[:ACTIVITY_LOOKBACK_LIMIT]
        )

    def _fallback(self, user_id, top_n):
        """Brand new user, zero activity yet -> trending/popular items."""
        result = {
            "jobs": self._popular_fallback("jobs", top_n),
            "services": self._popular_fallback("services", top_n),
        }
        self.cache.set(user_id, "jobs", result["jobs"])
        self.cache.set(user_id, "services", result["services"])
        return result

    def _popular_fallback(self, feed_type, top_n):
        """Cold-start / empty-feed source: trending items."""
        if feed_type == "jobs":
            from apps.jobs.selectors.job import (
                get_trending_jobs as get_trending,
            )
        else:
            from apps.services.selectors.services_selectors import (
                get_trending_services as get_trending,
            )

        return [
            {"id": str(obj.id), "score": 0} for obj in get_trending()[:top_n]
        ]
