from django.contrib import admin

from .models import OrganizationProfile, PersonalProfile, User

admin.site.register(User)
admin.site.register(OrganizationProfile)
admin.site.register(PersonalProfile)
