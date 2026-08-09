from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.generics import (
    DestroyAPIView,
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.locations.models import Location
from apps.locations.serializers import LocationSerializer
from apps.skill.models import Skill
from apps.users.models import (
    AdminProfile,
    OrganizationProfile,
    PersonalProfile,
    User,
)
from apps.users.permissions import CanManageAdminUser, HasPermission
from apps.users.serializers import AdminUpdateSerializer
from apps.utils.pagination import CustomPageNumberPagination


def _apply_location(user: User, validated_data: dict) -> None:
    """Pop location_* keys from validated_data and create/update user.location."""
    lat = validated_data.pop("location_lat", None)
    lng = validated_data.pop("location_lng", None)
    address = validated_data.pop("location_address", None)
    city = validated_data.pop("location_city", None)
    state = validated_data.pop("location_state", None)
    country = validated_data.pop("location_country", None)
    postal_code = validated_data.pop("location_postal_code", None)

    if (
        lat is None
        and lng is None
        and all(v is None for v in (address, city, state, country, postal_code))
    ):
        return

    location = user.location
    if location is None:
        location = Location(point=Point(lng or 0.0, lat or 0.0, srid=4326))
    elif lat is not None and lng is not None:
        location.point = Point(lng, lat, srid=4326)

    if address is not None:
        location.address = address
    if city is not None:
        location.city = city
    if state is not None:
        location.state = state
    if country is not None:
        location.country = country
    if postal_code is not None:
        location.postal_code = postal_code

    location.save()
    if user.location_id != location.id:
        user.location = location
        user.save(update_fields=["location"])


# --- Serializers ---


class SkillMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class PersonalProfileSerializer(serializers.ModelSerializer):
    skills = SkillMinimalSerializer(many=True, read_only=True)

    class Meta:
        model = PersonalProfile
        fields = [
            "id",
            "age",
            "gender",
            "skills",
            "interests",
            "created_at",
            "updated_at",
        ]


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationProfile
        fields = [
            "id",
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "is_verified",
            "created_at",
            "updated_at",
        ]


class AdminUserListSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    location_details = serializers.SerializerMethodField()
    is_onboarded = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "phone_number",
            "account_type",
            "status",
            "profile_visibility",
            "is_locked",
            "two_factor_enabled",
            "date_joined",
            "last_active_at",
            "avatar_url",
            "role",
            "location_details",
            "is_onboarded",
        ]

    def get_role(self, instance: User) -> dict[str, str] | None:
        admin_profile = getattr(instance, "admin_profile", None)
        if not admin_profile or not admin_profile.role_id:
            return None
        return {
            "code": admin_profile.role.code,
            "name": admin_profile.role.name,
        }

    def get_avatar_url(self, instance: User) -> str | None:
        request = self.context.get("request")
        return instance.get_absolute_avatar_url(request)

    def get_location_details(self, instance: User) -> dict | None:
        if not instance.location:
            return None
        return LocationSerializer(instance.location, context=self.context).data

    def get_is_onboarded(self, instance: User) -> bool:
        return instance.is_onboarded()


class AdminIndividualUserSerializer(AdminUserListSerializer):
    personal_profile = PersonalProfileSerializer(read_only=True)

    class Meta(AdminUserListSerializer.Meta):
        fields = [*AdminUserListSerializer.Meta.fields, "personal_profile"]


class AdminOrganizationUserSerializer(AdminUserListSerializer):
    organization_profile = OrganizationProfileSerializer(read_only=True)

    class Meta(AdminUserListSerializer.Meta):
        fields = [*AdminUserListSerializer.Meta.fields, "organization_profile"]


class AdminUserDetailSerializer(AdminUserListSerializer):
    personal_profile = PersonalProfileSerializer(read_only=True)
    organization_profile = OrganizationProfileSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    cover_photo_url = serializers.SerializerMethodField()
    admin_profile_details = serializers.SerializerMethodField()

    class Meta(AdminUserListSerializer.Meta):
        fields = [
            *AdminUserListSerializer.Meta.fields,
            "bio",
            "social_links",
            "last_login_at",
            "last_login_ip",
            "failed_login_attempts",
            "personal_profile",
            "organization_profile",
            "location",
            "cover_photo_url",
            "admin_profile_details",
        ]

    def get_cover_photo_url(self, instance: User) -> str | None:
        if not instance.cover_photo:
            return None
        request = self.context.get("request")
        url = instance.cover_photo.url
        return request.build_absolute_uri(url) if request else url

    def get_admin_profile_details(self, instance: User) -> dict | None:
        admin_profile = getattr(instance, "admin_profile", None)
        if not admin_profile:
            return None
        return {
            "department": admin_profile.department,
            "designation": admin_profile.designation,
            "ip_address": admin_profile.ip_address,
            "created_by": admin_profile.created_by.full_name
            if admin_profile.created_by_id
            else None,
            "created_at": admin_profile.created_at,
        }


class AdminCreateUserSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    account_type = serializers.ChoiceField(
        choices=[User.AccountType.PERSONAL, User.AccountType.ORGANIZATION]
    )
    status = serializers.ChoiceField(
        choices=User.Status.choices, default=User.Status.ACTIVE
    )
    profile_visibility = serializers.ChoiceField(
        choices=User.ProfileVisibility.choices,
        default=User.ProfileVisibility.PUBLIC,
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    cover_photo = serializers.ImageField(required=False, allow_null=True)

    # Location fields
    location_lat = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90
    )
    location_lng = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180
    )
    location_address = serializers.CharField(required=False, allow_blank=True)
    location_city = serializers.CharField(required=False, allow_blank=True)
    location_state = serializers.CharField(required=False, allow_blank=True)
    location_country = serializers.CharField(required=False, allow_blank=True)
    location_postal_code = serializers.CharField(
        required=False, allow_blank=True
    )

    # Personal profile fields
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=PersonalProfile.Gender.choices,
        required=False,
        default=PersonalProfile.Gender.NOT_SPECIFIED,
    )
    skill_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )

    # Organization profile fields
    industry = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    employees_count = serializers.IntegerField(required=False, allow_null=True)
    founded_at = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    tax_id = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        account_type = validated_data["account_type"]
        age = validated_data.pop("age", None)
        gender = validated_data.pop(
            "gender", PersonalProfile.Gender.NOT_SPECIFIED
        )
        skill_ids = validated_data.pop("skill_ids", [])
        industry = validated_data.pop("industry", "")
        employees_count = validated_data.pop("employees_count", None)
        founded_at = validated_data.pop("founded_at", None)
        address = validated_data.pop("address", "")
        tax_id = validated_data.pop("tax_id", "")
        location_data = {
            key: validated_data.pop(key)
            for key in [
                "location_lat",
                "location_lng",
                "location_address",
                "location_city",
                "location_state",
                "location_country",
                "location_postal_code",
            ]
            if key in validated_data
        }

        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        _apply_location(user, location_data)

        if account_type == User.AccountType.PERSONAL:
            profile = PersonalProfile.objects.create(
                user=user, age=age, gender=gender
            )
            if skill_ids:
                profile.skills.set(Skill.objects.filter(id__in=skill_ids))
        elif account_type == User.AccountType.ORGANIZATION:
            OrganizationProfile.objects.create(
                user=user,
                industry=industry,
                employees_count=employees_count,
                founded_at=founded_at,
                address=address,
                tax_id=tax_id,
            )

        return user


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    gender = serializers.ChoiceField(
        choices=PersonalProfile.Gender.choices, required=False, write_only=True
    )
    skill_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )
    industry = serializers.CharField(
        max_length=50, required=False, allow_blank=True, write_only=True
    )
    employees_count = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    founded_at = serializers.DateField(
        required=False, allow_null=True, write_only=True
    )
    address = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    tax_id = serializers.CharField(
        max_length=50, required=False, allow_blank=True, write_only=True
    )
    is_verified = serializers.BooleanField(required=False, write_only=True)
    password = serializers.CharField(
        required=False, allow_blank=True, write_only=True, min_length=8
    )
    location_lat = serializers.FloatField(
        required=False,
        allow_null=True,
        write_only=True,
        min_value=-90,
        max_value=90,
    )
    location_lng = serializers.FloatField(
        required=False,
        allow_null=True,
        write_only=True,
        min_value=-180,
        max_value=180,
    )
    location_address = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    location_city = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    location_state = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    location_country = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    location_postal_code = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "phone_number",
            "status",
            "profile_visibility",
            "is_locked",
            "bio",
            "profile_picture",
            "cover_photo",
            "password",
            "location_lat",
            "location_lng",
            "location_address",
            "location_city",
            "location_state",
            "location_country",
            "location_postal_code",
            "age",
            "gender",
            "skill_ids",
            "industry",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "is_verified",
        ]

    @transaction.atomic
    def update(self, instance: User, validated_data):
        age = validated_data.pop("age", None)
        gender = validated_data.pop("gender", None)
        skill_ids = validated_data.pop("skill_ids", None)
        industry = validated_data.pop("industry", None)
        employees_count = validated_data.pop("employees_count", None)
        founded_at = validated_data.pop("founded_at", None)
        address = validated_data.pop("address", None)
        tax_id = validated_data.pop("tax_id", None)
        is_verified = validated_data.pop("is_verified", None)
        password = validated_data.pop("password", None)
        location_data = {
            key: validated_data.pop(key)
            for key in [
                "location_lat",
                "location_lng",
                "location_address",
                "location_city",
                "location_state",
                "location_country",
                "location_postal_code",
            ]
            if key in validated_data
        }

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()

        _apply_location(instance, location_data)

        if instance.account_type == User.AccountType.PERSONAL:
            profile, _ = PersonalProfile.objects.get_or_create(user=instance)
            if age is not None:
                profile.age = age
            if gender is not None:
                profile.gender = gender
            if skill_ids is not None:
                profile.skills.set(Skill.objects.filter(id__in=skill_ids))
            profile.save()

        elif instance.account_type == User.AccountType.ORGANIZATION:
            profile, _ = OrganizationProfile.objects.get_or_create(
                user=instance
            )
            if industry is not None:
                profile.industry = industry
            if employees_count is not None:
                profile.employees_count = employees_count
            if founded_at is not None:
                profile.founded_at = founded_at
            if address is not None:
                profile.address = address
            if tax_id is not None:
                profile.tax_id = tax_id
            if is_verified is not None:
                profile.is_verified = is_verified
            profile.save()

        return instance


# --- Views ---


class AdminUserStatsView(GenericAPIView):
    permission_classes = [IsAuthenticated, HasPermission("users.view")]

    def get(self, request):
        total = User.objects.count()
        active = User.objects.filter(status=User.Status.ACTIVE).count()
        inactive = User.objects.filter(status=User.Status.INACTIVE).count()
        suspended = User.objects.filter(status=User.Status.SUSPENDED).count()
        blocked = User.objects.filter(status=User.Status.BLOCKED).count()
        personal = User.objects.filter(
            account_type=User.AccountType.PERSONAL
        ).count()
        organization = User.objects.filter(
            account_type=User.AccountType.ORGANIZATION
        ).count()
        admin_count = User.objects.filter(
            account_type=User.AccountType.ADMIN
        ).count()
        locked = User.objects.filter(is_locked=True).count()

        return Response(
            {
                "total": total,
                "active": active,
                "inactive": inactive,
                "suspended": suspended,
                "blocked": blocked,
                "personal": personal,
                "organization": organization,
                "admin": admin_count,
                "locked": locked,
            }
        )


class AdminAllUsersListView(ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = User.objects.select_related(
            "location", "admin_profile", "admin_profile__role"
        ).order_by("-date_joined")
        qs = qs.exclude(account_type=User.AccountType.ADMIN)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone_number__icontains=search)
            )

        account_type = self.request.query_params.get("account_type")
        if account_type:
            qs = qs.filter(account_type=account_type)

        user_status = self.request.query_params.get("status")
        if user_status:
            qs = qs.filter(status=user_status)

        profile_visibility = self.request.query_params.get("profile_visibility")
        if profile_visibility:
            qs = qs.filter(profile_visibility=profile_visibility)

        is_locked = self.request.query_params.get("is_locked")
        if is_locked is not None and is_locked != "":
            qs = qs.filter(is_locked=is_locked.lower() == "true")

        ordering = self.request.query_params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        return qs


class AdminIndividualsListView(ListAPIView):
    serializer_class = AdminIndividualUserSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = (
            User.objects.filter(account_type=User.AccountType.PERSONAL)
            .select_related("personal_profile", "location")
            .prefetch_related("personal_profile__skills")
            .order_by("-date_joined")
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone_number__icontains=search)
            )

        user_status = self.request.query_params.get("status")
        if user_status:
            qs = qs.filter(status=user_status)

        gender = self.request.query_params.get("gender")
        if gender:
            qs = qs.filter(personal_profile__gender=gender)

        min_age = self.request.query_params.get("min_age")
        if min_age:
            qs = qs.filter(personal_profile__age__gte=int(min_age))

        max_age = self.request.query_params.get("max_age")
        if max_age:
            qs = qs.filter(personal_profile__age__lte=int(max_age))

        skills = self.request.query_params.get("skills")
        if skills:
            skill_list = [s.strip() for s in skills.split(",") if s.strip()]
            qs = qs.filter(
                personal_profile__skills__id__in=skill_list
            ).distinct()

        ordering = self.request.query_params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        return qs


class AdminOrganizationsListView(ListAPIView):
    serializer_class = AdminOrganizationUserSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = (
            User.objects.filter(account_type=User.AccountType.ORGANIZATION)
            .select_related("organization_profile", "location")
            .order_by("-date_joined")
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(organization_profile__industry__icontains=search)
                | Q(organization_profile__tax_id__icontains=search)
            )

        user_status = self.request.query_params.get("status")
        if user_status:
            qs = qs.filter(status=user_status)

        industry = self.request.query_params.get("industry")
        if industry:
            qs = qs.filter(organization_profile__industry__icontains=industry)

        is_verified = self.request.query_params.get("is_verified")
        if is_verified is not None and is_verified != "":
            qs = qs.filter(
                organization_profile__is_verified=is_verified.lower() == "true"
            )

        min_employees = self.request.query_params.get("min_employees")
        if min_employees:
            qs = qs.filter(
                organization_profile__employees_count__gte=int(min_employees)
            )

        max_employees = self.request.query_params.get("max_employees")
        if max_employees:
            qs = qs.filter(
                organization_profile__employees_count__lte=int(max_employees)
            )

        ordering = self.request.query_params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        return qs


class AdminUserDetailView(RetrieveAPIView):
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    queryset = User.objects.select_related(
        "personal_profile",
        "organization_profile",
        "admin_profile",
        "admin_profile__role",
        "admin_profile__created_by",
        "location",
    ).prefetch_related("personal_profile__skills")
    lookup_field = "id"


class AdminCreateUserView(GenericAPIView):
    serializer_class = AdminCreateUserSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.edit")]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User created successfully.",
                "user": AdminUserDetailSerializer(
                    user, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminManageUserView(UpdateAPIView, DestroyAPIView):
    serializer_class = AdminUpdateUserSerializer
    queryset = User.objects.all()
    lookup_field = "id"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), HasPermission("users.delete")()]
        return [IsAuthenticated(), HasPermission("users.edit")()]

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        if user.account_type == User.AccountType.ADMIN:
            return Response(
                {
                    "detail": "Admin accounts must be managed from the Administration section."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        return Response(
            {
                "message": "User updated successfully.",
                "user": AdminUserDetailSerializer(
                    updated_user, context={"request": request}
                ).data,
            }
        )

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.account_type == User.AccountType.ADMIN:
            return Response(
                {
                    "detail": "Admin accounts must be managed from the Administration section."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()
        return Response(
            {"message": "User deleted successfully."}, status=status.HTTP_200_OK
        )


class AdminUserListView(ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    queryset = (
        User.objects.filter(account_type=User.AccountType.ADMIN)
        .select_related("admin_profile", "admin_profile__role")
        .order_by("-date_joined")
    )


class AdminUserUpdateView(UpdateAPIView):
    serializer_class = AdminUpdateSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "id"
    permission_classes = [
        IsAuthenticated,
        HasPermission("users.edit"),
        CanManageAdminUser,
    ]
    queryset = AdminProfile.objects.select_related("user", "role")

    def update(self, request, *args, **kwargs):
        admin_profile = self.get_object()
        serializer = self.get_serializer(
            admin_profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserListSerializer(admin_profile.user).data)


class CandidateUserListView(ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    queryset = User.objects.filter(
        account_type=User.AccountType.PERSONAL
    ).order_by("-date_joined")
