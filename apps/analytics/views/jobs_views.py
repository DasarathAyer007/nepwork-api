from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import HasPermission

from ..services.jobs_analytics_service import JobsAnalyticsService
from ..utils import cached_response, parse_date_range


@extend_schema(tags=["Analytics"])
class JobsTrendView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        date_from, date_to, granularity = parse_date_range(request.query_params)
        svc = JobsAnalyticsService(request.query_params)
        data = cached_response(
            "jobs:trend",
            request,
            lambda: svc.trend(date_from, date_to, granularity),
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class JobsStatusBreakdownView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        svc = JobsAnalyticsService(request.query_params)
        data = cached_response(
            "jobs:status-breakdown", request, svc.status_breakdown
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class JobsFunnelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        date_from, date_to, _ = parse_date_range(request.query_params)
        svc = JobsAnalyticsService(request.query_params)
        data = cached_response(
            "jobs:funnel", request, lambda: svc.funnel(date_from, date_to)
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class JobsCategoriesView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        sort = request.query_params.get("sort", "volume")
        svc = JobsAnalyticsService(request.query_params)
        data = cached_response(
            "jobs:categories",
            request,
            lambda: svc.top_categories(limit=limit, sort=sort),
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class JobsDeadlineHealthView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        svc = JobsAnalyticsService(request.query_params)
        data = cached_response(
            "jobs:deadline-health", request, svc.deadline_health
        )
        return Response(data)
