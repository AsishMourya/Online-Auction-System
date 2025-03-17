from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.permissions import IsAdmin
from apps.accounts.models import User
from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from .services import create_notification


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """Admin API for managing notifications"""

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_id="admin_list_notifications",
        operation_summary="List all notifications (Admin)",
        operation_description="Admin access to list notifications with filtering options",
        tags=["Admin - Notifications"],
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by user ID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
            ),
            openapi.Parameter(
                "notification_type",
                openapi.IN_QUERY,
                description="Filter by notification type",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "is_read",
                openapi.IN_QUERY,
                description="Filter by read status",
                type=openapi.TYPE_BOOLEAN,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset

        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(recipient_id=user_id)

        notification_type = request.query_params.get("notification_type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        is_read = request.query_params.get("is_read")
        if is_read is not None:
            is_read_bool = is_read.lower() == "true"
            queryset = queryset.filter(is_read=is_read_bool)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "Notifications retrieved successfully",
                "notifications": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="admin_delete_notification",
        operation_summary="Delete notification (Admin)",
        operation_description="Admin can delete any notification",
        tags=["Admin - Notifications"],
        responses={204: "No content", 404: "Not found"},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_id="admin_delete_read_notifications",
        operation_summary="Delete read notifications (Admin)",
        operation_description="Admin can delete all read notifications",
        tags=["Admin - Notifications"],
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Delete for specific user (optional)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=False,
            ),
        ],
        responses={204: "No content"},
    )
    @action(detail=False, methods=["delete"])
    def delete_read(self, request):
        user_id = request.query_params.get("user_id")

        if user_id:
            Notification.objects.filter(recipient_id=user_id, is_read=True).delete()
            return Response(
                {"message": f"All read notifications for user {user_id} deleted"},
                status=status.HTTP_200_OK,
            )

        Notification.objects.filter(is_read=True).delete()
        return Response(
            {"message": "All read notifications deleted system-wide"},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_send_notification",
    operation_summary="Send notification (Admin)",
    operation_description="Send notification to a user or group of users",
    tags=["Admin - Notifications"],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "recipient_ids": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
                ),
                description="List of user IDs to send notification to",
            ),
            "role": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Send to all users with this role",
                enum=["admin", "staff", "user"],
            ),
            "all_users": openapi.Schema(
                type=openapi.TYPE_BOOLEAN, description="Send to all users"
            ),
            "title": openapi.Schema(
                type=openapi.TYPE_STRING, description="Notification title"
            ),
            "message": openapi.Schema(
                type=openapi.TYPE_STRING, description="Notification message"
            ),
            "priority": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Notification priority",
                enum=["low", "medium", "high"],
                default="medium",
            ),
        },
        required=["title", "message"],
    ),
    responses={
        200: "Notification sent",
        400: "Bad request",
    },
)
def admin_send_notification(request):
    """Admin endpoint to send notifications to users"""

    title = request.data.get("title")
    message = request.data.get("message")
    priority = request.data.get("priority", "medium")

    if not title or not message:
        return Response(
            {"detail": "Title and message are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recipient_ids = request.data.get("recipient_ids", [])
    role = request.data.get("role")
    all_users = request.data.get("all_users", False)

    recipients = []

    if all_users:
        recipients = User.objects.all()
    elif role:
        recipients = User.objects.filter(role=role)
    elif recipient_ids:
        recipients = User.objects.filter(id__in=recipient_ids)
    else:
        return Response(
            {
                "detail": "You must specify recipients (recipient_ids, role, or all_users=true)."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    notification_count = 0
    for recipient in recipients:
        create_notification(
            recipient=recipient,
            notification_type=Notification.TYPE_ADMIN,
            title=title,
            message=message,
            priority=priority,
        )
        notification_count += 1

    return Response(
        {"message": f"Notification sent to {notification_count} users."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_notification_stats",
    operation_summary="Get notification statistics (Admin)",
    operation_description="Get statistics about notifications",
    tags=["Admin - Notifications"],
    responses={200: "Notification statistics"},
)
def admin_notification_stats(request):
    """Get notification statistics for admin dashboard"""
    total_notifications = Notification.objects.count()
    unread_notifications = Notification.objects.filter(is_read=False).count()

    by_type = Notification.objects.values("notification_type").annotate(
        count=Count("id")
    )

    by_priority = Notification.objects.values("priority").annotate(count=Count("id"))

    recent = Notification.objects.order_by("-created_at")[:10]
    recent_data = NotificationSerializer(recent, many=True).data

    return Response(
        {
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "by_type": list(by_type),
            "by_priority": list(by_priority),
            "recent_notifications": recent_data,
        }
    )
