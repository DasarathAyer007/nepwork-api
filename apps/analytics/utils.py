from datetime import date, datetime, timedelta

from django.db.models import Count, QuerySet
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.exceptions import ValidationError

DEFAULT_RANGE_DAYS = 30

TRUNC_FUNCS = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}


def parse_date_range(params: dict) -> tuple[date, date, str]:
    """Shared (date_from, date_to, granularity) parsing for every trend/
    funnel/breakdown endpoint. Defaults to the last 30 days, day
    granularity, when params are omitted."""
    granularity = params.get("granularity", "day")
    if granularity not in TRUNC_FUNCS:
        raise ValidationError(
            {"granularity": "Must be one of: day, week, month."}
        )

    today = timezone.now().date()
    date_to_raw = params.get("date_to")
    date_from_raw = params.get("date_from")

    try:
        date_to = (
            datetime.strptime(date_to_raw, "%Y-%m-%d").date()
            if date_to_raw
            else today
        )
        date_from = (
            datetime.strptime(date_from_raw, "%Y-%m-%d").date()
            if date_from_raw
            else date_to - timedelta(days=DEFAULT_RANGE_DAYS)
        )
    except ValueError:
        raise ValidationError(
            {"date_from/date_to": "Must be in YYYY-MM-DD format."}
        )

    if date_from > date_to:
        raise ValidationError({"date_from": "Must not be after date_to."})

    return date_from, date_to, granularity


def previous_period(date_from: date, date_to: date) -> tuple[date, date]:
    """The immediately preceding period of equal length, for
    period-over-period growth comparisons."""
    span = (date_to - date_from) + timedelta(days=1)
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - span + timedelta(days=1)
    return prev_from, prev_to


def growth_pct(current: int, previous: int) -> float | None:
    """Percent change vs. the prior period. None (not 0 or infinity) when
    there is no prior-period baseline to compare against."""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def trend_series(
    qs: QuerySet,
    date_field: str,
    date_from: date,
    date_to: date,
    granularity: str,
) -> list[dict]:
    """[{period, count}] time series, grouped by the requested granularity,
    over an inclusive date range."""
    trunc_fn = TRUNC_FUNCS[granularity]
    rows = (
        qs.filter(
            **{
                f"{date_field}__date__gte": date_from,
                f"{date_field}__date__lte": date_to,
            }
        )
        .annotate(period=trunc_fn(date_field))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )
    return [
        {"period": row["period"].date().isoformat(), "count": row["count"]}
        for row in rows
    ]


def status_counts(qs: QuerySet, choices, field: str = "status") -> dict:
    """Real per-`field` counts seeded with every choice (so values with
    zero rows still appear), matching the JobQueryService/ServiceQueryService
    status_counts() convention already used elsewhere in the project."""
    counts = {value: 0 for value, _ in choices}
    for row in qs.values(field).annotate(count=Count("id")):
        counts[row[field]] = row["count"]
    counts["total"] = sum(counts[value] for value, _ in choices)
    return counts


def conversion_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 1)


def cached_response(cache_prefix: str, request, compute_fn, timeout: int = 180):
    """Short-TTL Django-cache wrapper for the on-demand MVP endpoints,
    keyed by the endpoint's full querystring so distinct filter
    combinations don't collide."""
    from django.core.cache import cache

    key = f"analytics:{cache_prefix}:{request.get_full_path()}"
    return cache.get_or_set(key, compute_fn, timeout=timeout)
