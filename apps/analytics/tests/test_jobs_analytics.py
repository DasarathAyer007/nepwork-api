from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.jobs.models import Job, JobApplication, JobCategory
from apps.users.tests.factories import UserFactory

from ..services.jobs_analytics_service import JobsAnalyticsService


def _make_job(posted_by, category=None, status=Job.JobStatus.OPEN, **extra):
    return Job.objects.create(
        title="Frontend Developer",
        description="Build UIs",
        posted_by=posted_by,
        category=category,
        status=status,
        **extra,
    )


def _make_application(job, applicant, status, created_at=None):
    app = JobApplication.objects.create(
        job=job, applicant=applicant, status=status
    )
    if created_at:
        JobApplication.objects.filter(pk=app.pk).update(created_at=created_at)
        app.refresh_from_db()
    return app


class JobsAnalyticsServiceTests(TestCase):
    def setUp(self):
        self.employer = UserFactory()
        self.applicants = [UserFactory() for _ in range(4)]
        self.category = JobCategory.objects.create(name="Engineering")
        self.today = timezone.now().date()

    def test_status_breakdown_counts_every_choice(self):
        _make_job(self.employer, status=Job.JobStatus.OPEN)
        _make_job(self.employer, status=Job.JobStatus.OPEN)
        _make_job(self.employer, status=Job.JobStatus.CLOSED)

        breakdown = JobsAnalyticsService().status_breakdown()

        self.assertEqual(breakdown["open"], 2)
        self.assertEqual(breakdown["closed"], 1)
        self.assertEqual(breakdown["draft"], 0)
        self.assertEqual(breakdown["paused"], 0)
        self.assertEqual(breakdown["total"], 3)

    def test_funnel_conversion_rates(self):
        job = _make_job(self.employer)
        _make_application(
            job, self.applicants[0], JobApplication.ApplicationStatus.APPLIED
        )
        _make_application(
            job, self.applicants[1], JobApplication.ApplicationStatus.APPLIED
        )
        _make_application(
            job,
            self.applicants[2],
            JobApplication.ApplicationStatus.SHORTLISTED,
        )
        _make_application(
            job, self.applicants[3], JobApplication.ApplicationStatus.OFFERED
        )

        funnel = JobsAnalyticsService().funnel(
            self.today - timedelta(days=1), self.today + timedelta(days=1)
        )

        stage_counts = {s["status"]: s["count"] for s in funnel["stages"]}
        self.assertEqual(stage_counts["applied"], 2)
        self.assertEqual(stage_counts["shortlisted"], 1)
        self.assertEqual(stage_counts["offered"], 1)
        # 1 shortlisted / 2 applied = 50%
        self.assertEqual(
            funnel["conversion_rates"]["applied_to_shortlisted"], 50.0
        )
        self.assertEqual(funnel["total"], 4)
        self.assertEqual(funnel["drop_off_count"], 0)

    def test_funnel_excludes_applications_outside_date_range(self):
        job = _make_job(self.employer)
        old_app = _make_application(
            job, self.applicants[0], JobApplication.ApplicationStatus.APPLIED
        )
        JobApplication.objects.filter(pk=old_app.pk).update(
            created_at=timezone.now() - timedelta(days=90)
        )

        funnel = JobsAnalyticsService().funnel(
            self.today - timedelta(days=7), self.today
        )

        self.assertEqual(funnel["total"], 0)

    def test_top_categories_volume_and_conversion_sort(self):
        cat_a = JobCategory.objects.create(name="Design")
        cat_b = JobCategory.objects.create(name="Marketing")

        # cat_a: 2 jobs, 0 applications -> 0% conversion
        _make_job(self.employer, category=cat_a)
        _make_job(self.employer, category=cat_a)

        # cat_b: 1 job, 1 application -> 100% conversion, but lower volume
        job_b = _make_job(self.employer, category=cat_b)
        _make_application(
            job_b, self.applicants[0], JobApplication.ApplicationStatus.APPLIED
        )

        by_volume = JobsAnalyticsService().top_categories(sort="volume")
        self.assertEqual(by_volume[0]["category_name"], "Design")
        self.assertEqual(by_volume[0]["job_count"], 2)

        by_conversion = JobsAnalyticsService().top_categories(sort="conversion")
        self.assertEqual(by_conversion[0]["category_name"], "Marketing")
        self.assertEqual(by_conversion[0]["conversion_rate"], 100.0)

    def test_category_filter_scopes_all_metrics(self):
        cat_a = JobCategory.objects.create(name="Design")
        cat_b = JobCategory.objects.create(name="Marketing")
        _make_job(self.employer, category=cat_a, status=Job.JobStatus.OPEN)
        _make_job(self.employer, category=cat_b, status=Job.JobStatus.OPEN)

        breakdown = JobsAnalyticsService(
            {"category": str(cat_a.id)}
        ).status_breakdown()
        self.assertEqual(breakdown["total"], 1)

    def test_deadline_health_flags_stale_open_jobs(self):
        _make_job(
            self.employer,
            status=Job.JobStatus.OPEN,
            deadline=self.today - timedelta(days=5),
        )
        _make_job(
            self.employer,
            status=Job.JobStatus.OPEN,
            deadline=self.today + timedelta(days=5),
        )

        health = JobsAnalyticsService().deadline_health()
        self.assertEqual(health["open_past_deadline"], 1)

    def test_status_breakdown_not_skewed_by_multiple_applications(self):
        """Regression test: aggregating status counts must not fan out
        when a job has more than one related application row."""
        job = _make_job(self.employer, status=Job.JobStatus.OPEN)
        for applicant in self.applicants:
            _make_application(
                job, applicant, JobApplication.ApplicationStatus.APPLIED
            )

        breakdown = JobsAnalyticsService().status_breakdown()
        self.assertEqual(breakdown["open"], 1)
        self.assertEqual(breakdown["total"], 1)
