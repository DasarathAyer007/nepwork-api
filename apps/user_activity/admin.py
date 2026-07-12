from django.contrib import admin

from .models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "activity_type",
        "object_type",
        "object_id",
        "created_at",
    )
    list_filter = ("activity_type", "object_type", "created_at")
    search_fields = ("user__email", "object_id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
