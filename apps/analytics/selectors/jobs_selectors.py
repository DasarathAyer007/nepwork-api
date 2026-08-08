from apps.jobs.models import Job
from apps.jobs.selectors.application import get_applications_base


def get_jobs_for_analytics(category=None):
    """A plain, unannotated queryset of every non-deleted job. Deliberately
    NOT apps.jobs.selectors.job.get_base_job_queryset — that selector's own
    total_applications=Count("applications") annotation causes a JOIN
    fan-out when combined with a further .values().annotate(Count("id")),
    silently overcounting any job with more than one application."""
    qs = Job.objects.filter(deleted_at__isnull=True)
    if category:
        qs = qs.filter(category_id=category)
    return qs


def get_job_applications_for_analytics(category=None):
    qs = get_applications_base()
    if category:
        qs = qs.filter(job__category_id=category)
    return qs
