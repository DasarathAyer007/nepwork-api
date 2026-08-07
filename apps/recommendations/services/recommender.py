"""
Recommendation pipeline: recent activity -> weighted preference -> candidate
pool -> scored ranking -> cached result.

Single entry point: generate_for_user(user_id, top_n=20)
"""

from collections import defaultdict

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.user_activity.constants import (
    ACTIVITY_WEIGHTS,
    ActivityType,
    ObjectType,
)

from .cache import RecommendationCache

ACTIVITY_LOOKBACK_LIMIT = 500  # most recent N events considered per user
MAX_CANDIDATES_PER_FEED = getattr(
    settings, "RECOMMENDATION_CANDIDATE_POOL_SIZE", 500
)

# How much weight decays for older events, so recent behaviour dominates.
RECENCY_MULTIPLIERS = (
    (7, 1.0),  # last 7 days -> full weight
    (30, 0.6),  # 8-30 days -> 60%
    (90, 0.3),  # 31-90 days -> 30%
)

# Relative importance of each scoring signal.
SIGNAL_WEIGHTS = {
    "category": 0.45,
    "skill": 0.35,
    "popularity": 0.15,
    "freshness": 0.05,
}

# feed_type -> preference key prefix, skills relation, popularity field
FEEDS = {
    "jobs": {
        "prefix": "job",
        "skills_field": "skills_required",
        "popularity_field": "total_applications",
    },
    "services": {
        "prefix": "service",
        "skills_field": "skills",
        "popularity_field": "total_applies",
    },
}


def _recency_multiplier(days_old: int) -> float:
    for max_days, multiplier in RECENCY_MULTIPLIERS:
        if days_old <= max_days:
            return multiplier
    return 0.1  # anything older than 90 days barely counts


def generate_for_user(
    user_id, top_n=20, cache: RecommendationCache | None = None
) -> dict:
    """
    Ranks jobs/services from the user's recent activity and caches each feed
    that got a real personalized ranking. Cold-start/empty feeds fall back to
    trending items, computed fresh and returned uncached every time.
    """
    cache = cache or RecommendationCache()
    activities = _get_recent_activities(user_id)
    preference = (
        build_preference(activities, timezone.now()) if activities else None
    )

    result = {}
    for feed_type in FEEDS:
        ranked = _rank_feed(feed_type, preference, top_n) if preference else []
        if ranked:
            cache.set(user_id, feed_type, ranked)
        else:
            ranked = _popular_fallback(feed_type, top_n)
        result[feed_type] = ranked
    return result


def _get_recent_activities(user_id):
    from apps.user_activity.models import UserActivity

    return list(
        UserActivity.objects.filter(user_id=user_id).order_by("-created_at")[
            :ACTIVITY_LOOKBACK_LIMIT
        ]
    )


# ── Preference: activity rows -> weighted category/skill profile ──────────


def build_preference(activities, now) -> dict:
    """
    {
        "job_categories": {category_id: weight}, "service_categories": {...},
        "job_skills": {skill_id: weight}, "service_skills": {...},
        "job_ids_seen": {job_id, ...}, "service_ids_seen": {...},
        "job_ids_applied": {job_id, ...}, "service_ids_requested": {...},
    }
    """
    job_ids = {
        a.object_id
        for a in activities
        if a.object_type == ObjectType.JOB and a.object_id
    }
    service_ids = {
        a.object_id
        for a in activities
        if a.object_type == ObjectType.SERVICE and a.object_id
    }
    job_category_map, job_skill_map = _lookup_maps("job", job_ids)
    service_category_map, service_skill_map = _lookup_maps(
        "service", service_ids
    )

    preference = {
        "job_categories": defaultdict(float),
        "service_categories": defaultdict(float),
        "job_skills": defaultdict(float),
        "service_skills": defaultdict(float),
        "job_ids_seen": set(),
        "service_ids_seen": set(),
        "job_ids_applied": set(),
        "service_ids_requested": set(),
    }

    for activity in activities:
        if (
            activity.activity_type == ActivityType.SEARCH
            or not activity.object_id
        ):
            continue  # no associated object to score preferences from

        weight = ACTIVITY_WEIGHTS.get(
            activity.activity_type, 1
        ) * _recency_multiplier((now - activity.created_at).days)
        object_id = activity.object_id

        if activity.object_type == ObjectType.JOB:
            preference["job_ids_seen"].add(object_id)
            if activity.activity_type == ActivityType.APPLY:
                preference["job_ids_applied"].add(object_id)
            _accumulate(
                object_id,
                weight,
                job_category_map,
                job_skill_map,
                preference["job_categories"],
                preference["job_skills"],
            )
        elif activity.object_type == ObjectType.SERVICE:
            preference["service_ids_seen"].add(object_id)
            if activity.activity_type == ActivityType.REQUEST:
                preference["service_ids_requested"].add(object_id)
            _accumulate(
                object_id,
                weight,
                service_category_map,
                service_skill_map,
                preference["service_categories"],
                preference["service_skills"],
            )

    for key in (
        "job_categories",
        "service_categories",
        "job_skills",
        "service_skills",
    ):
        preference[key] = dict(preference[key])
    return preference


def _accumulate(object_id, weight, category_map, skill_map, categories, skills):
    category_id = category_map.get(object_id)
    if category_id:
        categories[category_id] += weight

    skill_ids = skill_map.get(object_id) or set()
    if skill_ids:
        per_skill_weight = weight / len(skill_ids)
        for skill_id in skill_ids:
            skills[skill_id] += per_skill_weight


def _lookup_maps(prefix, object_ids: set) -> tuple[dict, dict]:
    """Batch category_id + skill_ids lookup for touched Job/Service rows."""
    if not object_ids:
        return {}, {}

    if prefix == "job":
        from apps.jobs.models import Job as Model

        skills_through = Model.skills_required.through
        skill_fk = "job_id"
    else:
        from apps.services.models import Service as Model

        skills_through = Model.skills.through
        skill_fk = "service_id"

    category_map = {
        str(pk): category_id
        for pk, category_id in Model.objects.filter(
            id__in=object_ids
        ).values_list("id", "category_id")
    }
    skill_map = defaultdict(set)
    for object_id, skill_id in skills_through.objects.filter(
        **{f"{skill_fk}__in": object_ids}
    ).values_list(skill_fk, "skill_id"):
        skill_map[str(object_id)].add(skill_id)

    return category_map, dict(skill_map)


# ── Candidates + scoring, per feed ─────────────────────────────────────────


def _rank_feed(feed_type, preference, top_n):
    candidates = _get_candidates(feed_type, preference)
    if not candidates:
        return []
    return _score(feed_type, candidates, preference)[:top_n]


def _get_candidates(feed_type, preference, limit=MAX_CANDIDATES_PER_FEED):
    prefix = FEEDS[feed_type]["prefix"]
    category_ids = list(preference[f"{prefix}_categories"].keys())
    if not category_ids:
        return []
    excluded_ids = preference[f"{prefix}_ids_seen"] | (
        preference["job_ids_applied"]
        if feed_type == "jobs"
        else preference["service_ids_requested"]
    )

    if feed_type == "jobs":
        from apps.jobs.models import Job

        return list(
            Job.objects.filter(
                category_id__in=category_ids, status=Job.JobStatus.OPEN
            )
            .exclude(deadline__lt=timezone.now().date())
            .exclude(id__in=excluded_ids)
            .only("id", "category_id", "created_at")
            .prefetch_related("skills_required")
            .annotate(total_applications=Count("applications"))
            .order_by("-created_at")[:limit]
        )

    from apps.services.models import Service

    return list(
        Service.objects.filter(
            category_id__in=category_ids, status=Service.ServiceStatus.ACTIVE
        )
        .exclude(id__in=excluded_ids)
        .only("id", "category_id", "created_at")
        .prefetch_related("skills")
        .order_by("-created_at")[:limit]
    )


def _score(feed_type, candidates, preference):
    config = FEEDS[feed_type]
    prefix = config["prefix"]
    category_scores = preference[f"{prefix}_categories"]
    skill_scores = preference[f"{prefix}_skills"]
    seen = preference[f"{prefix}_ids_seen"]
    skills_field = config["skills_field"]
    popularity_field = config["popularity_field"]

    pool = [c for c in candidates if str(c.id) not in seen]
    if not pool:
        return []

    max_category = max(category_scores.values(), default=0) or 1
    max_skill = max(skill_scores.values(), default=0) or 1
    max_popularity = (
        max((getattr(c, popularity_field, 0) or 0 for c in pool), default=0)
        or 1
    )
    now = timezone.now()

    results = []
    for candidate in pool:
        category_score = (
            category_scores.get(candidate.category_id, 0) / max_category
        )

        candidate_skill_ids = {
            s.id for s in getattr(candidate, skills_field).all()
        }
        skill_overlap = sum(
            skill_scores.get(sid, 0) for sid in candidate_skill_ids
        )
        skill_score = (
            min(skill_overlap / max_skill, 1.0) if candidate_skill_ids else 0.0
        )

        if category_score <= 0 and skill_score <= 0:
            continue  # no relevance signal at all, don't recommend

        popularity_score = (
            getattr(candidate, popularity_field, 0) or 0
        ) / max_popularity
        freshness_score = _recency_multiplier((now - candidate.created_at).days)

        score = (
            category_score * SIGNAL_WEIGHTS["category"]
            + skill_score * SIGNAL_WEIGHTS["skill"]
            + popularity_score * SIGNAL_WEIGHTS["popularity"]
            + freshness_score * SIGNAL_WEIGHTS["freshness"]
        )
        results.append({"id": str(candidate.id), "score": round(score, 4)})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def _popular_fallback(feed_type, top_n):
    """Cold-start / empty-feed source: trending items, never cached."""
    if feed_type == "jobs":
        from apps.jobs.selectors.job import get_trending_jobs as get_trending
    else:
        from apps.services.selectors.services_selectors import (
            get_trending_services as get_trending,
        )

    return [{"id": str(obj.id), "score": 0} for obj in get_trending()[:top_n]]
