from drf_spectacular.utils import (
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
)

from .serializers import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)

ONBOARDING_SCHEMA = extend_schema(
    request=PolymorphicProxySerializer(
        component_name="CreateProfileRequest",
        serializers=[
            PersonalProfileWriteSerializer,
            OrganizationProfileWriteSerializer,
        ],
        resource_type_field_name="account_type",
    ),
    responses={
        201: OpenApiResponse(
            description="Profile created successfully",
        ),
        403: OpenApiResponse(
            description="Authentication required or onboarding not allowed",
        ),
    },
)
