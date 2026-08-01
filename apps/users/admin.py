from django.contrib import admin

from .models import (
    AdminProfile,
    OrganizationProfile,
    Permission,
    PersonalProfile,
    Role,
    RolePermission,
    User,
    UserPermission,
)

admin.site.register(User)
admin.site.register(OrganizationProfile)
admin.site.register(PersonalProfile)
admin.site.register(AdminProfile)
admin.site.register(Role)
admin.site.register(RolePermission)
admin.site.register(Permission)
admin.site.register(UserPermission)
