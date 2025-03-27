from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, NotificationPreferenceViewSet
from .admin_views import (
    AdminNotificationViewSet,
    admin_send_notification,
    admin_notification_stats,
)

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(
    r"preferences", NotificationPreferenceViewSet, basename="notification-preference"
)

admin_router = DefaultRouter()
admin_router.register(
    r"notifications", AdminNotificationViewSet, basename="admin-notification"
)

urlpatterns = [
    # Standard API endpoints
    path("", include(router.urls)),
    # Admin API endpoints
    path("admin/", include(admin_router.urls)),
    path("admin/send/", admin_send_notification, name="admin-send-notification"),
    path("admin/stats/", admin_notification_stats, name="admin-notification-stats"),
]
