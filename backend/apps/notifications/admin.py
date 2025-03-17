from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_type",
        "recipient",
        "title",
        "is_read",
        "priority",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "priority", "created_at")
    search_fields = ("title", "message", "recipient__email")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("recipient", "notification_type", "title", "message")}),
        ("Status", {"fields": ("is_read", "priority")}),
        ("Related Object", {"fields": ("related_object_id", "related_object_type")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bid_notifications",
        "outbid_notifications",
        "auction_won_notifications",
    )
    search_fields = ("user__email",)
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Notification Types",
            {
                "fields": (
                    "bid_notifications",
                    "outbid_notifications",
                    "auction_won_notifications",
                    "auction_ended_notifications",
                    "payment_notifications",
                    "admin_notifications",
                )
            },
        ),
        ("Delivery Channels", {"fields": ("preferred_channels",)}),
    )
