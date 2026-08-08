from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.services.models import Service, ServiceCategory, ServiceRequest
from apps.users.tests.factories import UserFactory

from ..services.services_analytics_service import ServicesAnalyticsService


def _make_service(
    user, category=None, status=Service.ServiceStatus.ACTIVE, **extra
):
    return Service.objects.create(
        title="Logo Design",
        user=user,
        category=category,
        status=status,
        **extra,
    )


def _make_request(service, requester, status, created_at=None):
    req = ServiceRequest.objects.create(
        service=service, user=requester, status=status
    )
    if created_at:
        ServiceRequest.objects.filter(pk=req.pk).update(created_at=created_at)
        req.refresh_from_db()
    return req


class ServicesAnalyticsServiceTests(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.customers = [UserFactory() for _ in range(4)]
        self.today = timezone.now().date()

    def test_status_breakdown_counts_every_choice(self):
        _make_service(self.provider, status=Service.ServiceStatus.ACTIVE)
        _make_service(self.provider, status=Service.ServiceStatus.ACTIVE)
        _make_service(self.provider, status=Service.ServiceStatus.PAUSED)

        breakdown = ServicesAnalyticsService().status_breakdown()

        self.assertEqual(breakdown["active"], 2)
        self.assertEqual(breakdown["paused"], 1)
        self.assertEqual(breakdown["draft"], 0)
        self.assertEqual(breakdown["total"], 3)

    def test_availability_breakdown_uses_availability_field_not_status(self):
        _make_service(
            self.provider,
            availability_status=Service.AvailabilityStatus.AVAILABLE,
        )
        _make_service(
            self.provider,
            availability_status=Service.AvailabilityStatus.ON_BREAK,
        )

        breakdown = ServicesAnalyticsService().availability_breakdown()

        self.assertEqual(breakdown["available"], 1)
        self.assertEqual(breakdown["break"], 1)
        self.assertEqual(breakdown["unavailable"], 0)
        self.assertEqual(breakdown["holiday"], 0)
        self.assertEqual(breakdown["total"], 2)
        self.assertNotIn("active", breakdown)

    def test_funnel_conversion_rates(self):
        service = _make_service(self.provider)
        _make_request(
            service,
            self.customers[0],
            ServiceRequest.ServiceRequestStatus.OPEN,
        )
        _make_request(
            service,
            self.customers[1],
            ServiceRequest.ServiceRequestStatus.OPEN,
        )
        _make_request(
            service,
            self.customers[2],
            ServiceRequest.ServiceRequestStatus.ACCEPTED,
        )
        _make_request(
            service,
            self.customers[3],
            ServiceRequest.ServiceRequestStatus.COMPLETED,
        )

        funnel = ServicesAnalyticsService().funnel(
            self.today - timedelta(days=1), self.today + timedelta(days=1)
        )

        stage_counts = {s["status"]: s["count"] for s in funnel["stages"]}
        self.assertEqual(stage_counts["open"], 2)
        self.assertEqual(stage_counts["accepted"], 1)
        self.assertEqual(stage_counts["completed"], 1)
        self.assertEqual(funnel["conversion_rates"]["open_to_accepted"], 50.0)
        self.assertEqual(funnel["total"], 4)

    def test_top_categories_request_count_not_skewed_by_fan_out(self):
        cat = ServiceCategory.objects.create(name="Home Repair")
        service = _make_service(self.provider, category=cat)
        for customer in self.customers:
            _make_request(
                service, customer, ServiceRequest.ServiceRequestStatus.OPEN
            )

        rows = ServicesAnalyticsService().top_categories()
        row = next(r for r in rows if r["category_name"] == "Home Repair")
        self.assertEqual(row["service_count"], 1)
        self.assertEqual(row["request_count"], 4)

    def test_summary_reports_growth_and_conversion(self):
        service = _make_service(self.provider)
        _make_request(
            service,
            self.customers[0],
            ServiceRequest.ServiceRequestStatus.COMPLETED,
        )

        summary = ServicesAnalyticsService().summary(
            self.today - timedelta(days=1), self.today + timedelta(days=1)
        )

        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["requests_total"], 1)
        self.assertEqual(summary["conversion_open_to_completed_pct"], 100.0)
