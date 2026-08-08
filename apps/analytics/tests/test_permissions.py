from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import AdminProfile, Permission, Role, RolePermission
from apps.users.tests.factories import UserFactory


class AnalyticsPermissionTests(APITestCase):
    url = "/api/analytics/summary/"

    def setUp(self):
        role = Role.objects.create(code="admin", name="Admin")
        permission = Permission.objects.create(
            code="analytics.view", name="Analytics View"
        )
        RolePermission.objects.create(role=role, permission=permission)

        self.admin_with_access = UserFactory(account_type="admin")
        AdminProfile.objects.create(user=self.admin_with_access, role=role)

        self.personal_user = UserFactory(account_type="personal")

    def test_unauthenticated_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_authenticate(self.personal_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_with_analytics_view_permission_is_allowed(self):
        self.client.force_authenticate(self.admin_with_access)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_bypasses_permission_check(self):
        superuser = UserFactory(account_type="admin", is_superuser=True)
        self.client.force_authenticate(superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
