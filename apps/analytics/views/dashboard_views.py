from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import HasPermission

from ..services.summary_service import DashboardSummaryService
from ..utils import cached_response, parse_date_range


@extend_schema(tags=["Analytics"])
class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("analytics.view")]

    def get(self, request):
        date_from, date_to, _ = parse_date_range(request.query_params)
        svc = DashboardSummaryService(request.query_params)
        data = cached_response(
            "summary", request, lambda: svc.summary(date_from, date_to)
        )
        return Response(data)
