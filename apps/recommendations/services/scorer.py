from collections import defaultdict

from django.utils import timezone

from apps.user_activity.constants import (
    ACTIVITY_WEIGHTS,
    ActivityType,
    ObjectType,
)

# How much weight decays for older events, so recent behaviour dominates.
RECENCY_MULTIPLIERS = (
    (7, 1.0),  # last 7 days -> full weight
    (30, 0.6),  # 8-30 days -> 60%
    (90, 0.3),  # 31-90 days -> 30%
)


def _recency_multiplier(days_old: int) -> float:
    for max_days, multiplier in RECENCY_MULTIPLIERS:
        if days_old <= max_days:
            return multiplier
    return 0.1  # anything older than 90 days barely counts


class UserPreferenceBuilder:
    """
    Turns a list of UserActivity rows into a weighted preference profile:

        {
            "job_categories": {category_id: weight},
            "service_categories": {category_id: weight},
            "job_skills": {skill_id: weight},
            "service_skills": {skill_id: weight},
            "job_ids_seen": {job_id, ...},          # any interaction, for de-dup
            "service_ids_seen": {service_id, ...},
            "job_ids_applied": {job_id, ...},        # feeds candidate exclusion
            "service_ids_requested": {service_id, ...},
        }

    Category/skill lookups for the touched Job/Service rows are batched
    up-front (one query per model per relation) instead of hitting the DB
    once per activity row.
    """

    def build(self, activities, now) -> dict:
        job_categories: defaultdict = defaultdict(float)
        service_categories: defaultdict = defaultdict(float)
        job_skills: defaultdict = defaultdict(float)
        service_skills: defaultdict = defaultdict(float)
        job_ids_seen: set = set()
        service_ids_seen: set = set()
        job_ids_applied: set = set()
        service_ids_requested: set = set()

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
        job_category_map, job_skill_map = self._job_lookup_maps(job_ids)
        service_category_map, service_skill_map = self._service_lookup_maps(
            service_ids
        )

        for activity in activities:
            if activity.activity_type == ActivityType.SEARCH:
                continue  # no associated object to score preferences from

            weight = ACTIVITY_WEIGHTS.get(
                activity.activity_type, 1
            ) * _recency_multiplier((now - activity.created_at).days)
            object_id = activity.object_id
            if not object_id:
                continue

            if activity.object_type == ObjectType.JOB:
                job_ids_seen.add(object_id)
                if activity.activity_type == ActivityType.APPLY:
                    job_ids_applied.add(object_id)
                self._accumulate(
                    object_id,
                    weight,
                    job_category_map,
                    job_skill_map,
                    job_categories,
                    job_skills,
                )

            elif activity.object_type == ObjectType.SERVICE:
                service_ids_seen.add(object_id)
                if activity.activity_type == ActivityType.REQUEST:
                    service_ids_requested.add(object_id)
                self._accumulate(
                    object_id,
                    weight,
                    service_category_map,
                    service_skill_map,
                    service_categories,
                    service_skills,
                )

        return {
            "job_categories": dict(job_categories),
            "service_categories": dict(service_categories),
            "job_skills": dict(job_skills),
            "service_skills": dict(service_skills),
            "job_ids_seen": job_ids_seen,
            "service_ids_seen": service_ids_seen,
            "job_ids_applied": job_ids_applied,
            "service_ids_requested": service_ids_requested,
        }

    @staticmethod
    def _accumulate(
        object_id, weight, category_map, skill_map, categories, skills
    ):
        category_id = category_map.get(object_id)
        if category_id:
            categories[category_id] += weight

        skill_ids = skill_map.get(object_id) or set()
        if skill_ids:
            per_skill_weight = weight / len(skill_ids)
            for skill_id in skill_ids:
                skills[skill_id] += per_skill_weight

    def _job_lookup_maps(self, job_ids: set) -> tuple[dict, dict]:
        from apps.jobs.models import Job

        if not job_ids:
            return {}, {}

        category_map = {
            str(pk): category_id
            for pk, category_id in Job.objects.filter(
                id__in=job_ids
            ).values_list("id", "category_id")
        }
        skill_map: defaultdict = defaultdict(set)
        for job_id, skill_id in Job.skills_required.through.objects.filter(
            job_id__in=job_ids
        ).values_list("job_id", "skill_id"):
            skill_map[str(job_id)].add(skill_id)

        return category_map, dict(skill_map)

    def _service_lookup_maps(self, service_ids: set) -> tuple[dict, dict]:
        from apps.services.models import Service

        if not service_ids:
            return {}, {}

        category_map = {
            str(pk): category_id
            for pk, category_id in Service.objects.filter(
                id__in=service_ids
            ).values_list("id", "category_id")
        }
        skill_map: defaultdict = defaultdict(set)
        for service_id, skill_id in Service.skills.through.objects.filter(
            service_id__in=service_ids
        ).values_list("service_id", "skill_id"):
            skill_map[str(service_id)].add(skill_id)

        return category_map, dict(skill_map)


# Relative importance of each scoring signal.
SIGNAL_WEIGHTS = {
    "category": 0.45,
    "skill": 0.35,
    "popularity": 0.15,
    "freshness": 0.05,
}


class CandidateScorer:
    """
    Scores a queryset of candidate Job/Service objects against the user's
    preference profile. Pure function of (candidates, preference) -> ranked
    list of {"id", "score"} sorted descending.
    """

    def score_jobs(self, candidates, preference: dict) -> list[dict]:
        return self._score(
            candidates,
            category_scores=preference["job_categories"],
            skill_scores=preference["job_skills"],
            seen=preference["job_ids_seen"],
            skills_field="skills_required",
            popularity_field="total_applications",
        )

    def score_services(self, candidates, preference: dict) -> list[dict]:
        return self._score(
            candidates,
            category_scores=preference["service_categories"],
            skill_scores=preference["service_skills"],
            seen=preference["service_ids_seen"],
            skills_field="skills",
            popularity_field="total_applies",
        )

    def _score(
        self,
        candidates,
        category_scores,
        skill_scores,
        seen,
        skills_field,
        popularity_field,
    ):
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
                min(skill_overlap / max_skill, 1.0)
                if candidate_skill_ids
                else 0.0
            )

            if category_score <= 0 and skill_score <= 0:
                continue  # no relevance signal at all, don't recommend

            popularity_score = (
                getattr(candidate, popularity_field, 0) or 0
            ) / max_popularity
            freshness_score = _recency_multiplier(
                (now - candidate.created_at).days
            )

            score = (
                category_score * SIGNAL_WEIGHTS["category"]
                + skill_score * SIGNAL_WEIGHTS["skill"]
                + popularity_score * SIGNAL_WEIGHTS["popularity"]
                + freshness_score * SIGNAL_WEIGHTS["freshness"]
            )
            results.append({"id": str(candidate.id), "score": round(score, 4)})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results
