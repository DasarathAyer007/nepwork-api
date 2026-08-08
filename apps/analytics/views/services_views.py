from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import HasPermission

from ..services.services_analytics_service import ServicesAnalyticsService
from ..utils import cached_response, parse_date_range


@extend_schema(tags=["Analytics"])
class ServicesTrendView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        date_from, date_to, granularity = parse_date_range(request.query_params)
        svc = ServicesAnalyticsService(request.query_params)
        data = cached_response(
            "services:trend",
            request,
            lambda: svc.trend(date_from, date_to, granularity),
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class ServicesStatusBreakdownView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        svc = ServicesAnalyticsService(request.query_params)
        data = cached_response(
            "services:status-breakdown", request, svc.status_breakdown
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class ServicesAvailabilityBreakdownView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        svc = ServicesAnalyticsService(request.query_params)
        data = cached_response(
            "services:availability-breakdown",
            request,
            svc.availability_breakdown,
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class ServicesFunnelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        date_from, date_to, _ = parse_date_range(request.query_params)
        svc = ServicesAnalyticsService(request.query_params)
        data = cached_response(
            "services:funnel", request, lambda: svc.funnel(date_from, date_to)
        )
        return Response(data)


@extend_schema(tags=["Analytics"])
class ServicesCategoriesView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        sort = request.query_params.get("sort", "volume")
        svc = ServicesAnalyticsService(request.query_params)
        data = cached_response(
            "services:categories",
            request,
            lambda: svc.top_categories(limit=limit, sort=sort),
        )
        return Response(data)
