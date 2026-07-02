from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)

from apps.locations.serializers import (
    LocationSerializer,
    LocationWriteSerializer,
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


USER_LOCATION_SCHEMA = extend_schema_view(
    get=extend_schema(
        tags=["User Location"],
        operation_id="get_user_location",
        summary="Get user location",
        description="""
Returns a user's location according to the location's visibility level.

Visibility rules:

- **Exact** → Full address and coordinates.
- **Street** → Address, city, state, country, postal code.
- **Area** → City, state, country, postal code.
- **City** → City, state, country.
- **State** → State and country.
- **Country** → Country only.
- **Hidden** → Label only (e.g. Home, Office).
- **Private** → `null`.

If the authenticated user is requesting **their own location**, the full location is always returned regardless of the visibility level.
""",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                required=True,
                description="UUID of the user.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=LocationSerializer,
                description="Location returned according to visibility settings.",
            ),
            404: OpenApiResponse(
                description="The user has not set a location."
            ),
        },
        examples=[
            OpenApiExample(
                "Exact visibility",
                value={
                    "point": {
                        "lat": 27.7172,
                        "lng": 85.3240,
                    },
                    "address": "Putalisadak",
                    "city": "Kathmandu",
                    "state": "Bagmati",
                    "country": "Nepal",
                    "postal_code": "44600",
                    "label": "Home",
                },
                response_only=True,
            ),
            OpenApiExample(
                "City visibility",
                value={
                    "city": "Kathmandu",
                    "state": "Bagmati",
                    "country": "Nepal",
                },
                response_only=True,
            ),
            OpenApiExample(
                "Country visibility",
                value={
                    "country": "Nepal",
                },
                response_only=True,
            ),
            OpenApiExample(
                "Hidden visibility",
                value={
                    "label": "Home",
                },
                response_only=True,
            ),
            OpenApiExample(
                "Private visibility",
                value=None,
                response_only=True,
            ),
        ],
    ),
    post=extend_schema(
        tags=["User Location"],
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
            )
        ],
        request=LocationWriteSerializer,
        responses={
            200: LocationSerializer,
            403: OpenApiResponse(description="Not allowed"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Create or update a user's location (owner only).",
    ),
    put=extend_schema(
        tags=["User Location"],
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
            )
        ],
        request=LocationWriteSerializer,
        responses={
            200: LocationSerializer,
            404: OpenApiResponse(description="Location not found"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Fully update a user's location (owner only).",
    ),
)
