from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsOwner
from apps.core.mixins import SwaggerSchemaMixin, ApiResponseMixin
from apps.core.responses import api_response

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for managing user notifications"""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        """Return notifications for the current user"""
        user = self.request.user
        if user.role == "admin" and "user_id" in self.request.query_params:
            user_id = self.request.query_params.get("user_id")
            return Notification.objects.filter(recipient_id=user_id).order_by(
                "-created_at"
            )
        return Notification.objects.filter(recipient=user).order_by("-created_at")

    def get_permissions(self):
        """Only allow users to access their own notifications"""
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated, IsOwner]
        return super().get_permissions()

    @swagger_auto_schema(
        operation_id="list_notifications",
        operation_summary="Get user notifications",
        operation_description="Get all notifications for the current user",
        tags=["Notifications"],
        manual_parameters=[
            openapi.Parameter(
                "unread_only",
                openapi.IN_QUERY,
                description="Filter for unread notifications only",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                "notification_type",
                openapi.IN_QUERY,
                description="Filter by notification type",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: NotificationSerializer(many=True)},
        security=[{"Bearer": []}],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        unread_only = request.query_params.get("unread_only", "false").lower() == "true"
        if unread_only:
            queryset = queryset.filter(is_read=False)

        notification_type = request.query_params.get("notification_type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data, message="Notifications retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="retrieve_notification",
        operation_summary="Get notification details",
        operation_description="Get details of a specific notification",
        tags=["Notifications"],
        responses={200: NotificationSerializer, 404: "Not found"},
        security=[{"Bearer": []}],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            data=serializer.data, message="Notification details retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="mark_read",
        operation_summary="Mark notification as read",
        operation_description="Mark a specific notification as read",
        tags=["Notifications"],
        responses={200: NotificationSerializer, 404: "Not found"},
        security=[{"Bearer": []}],
    )
    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        serializer = self.get_serializer(notification)
        return api_response(data=serializer.data, message="Notification marked as read")

    @swagger_auto_schema(
        operation_id="mark_all_read",
        operation_summary="Mark all notifications as read",
        operation_description="Mark all user notifications as read",
        tags=["Notifications"],
        responses={200: "All notifications marked as read"},
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        queryset = self.get_queryset()
        queryset.update(is_read=True)
        return api_response(message="All notifications marked as read")

    @swagger_auto_schema(
        operation_id="delete_notification",
        operation_summary="Delete notification",
        operation_description="Delete a specific notification",
        tags=["Notifications"],
        responses={204: "No content", 404: "Not found"},
        security=[{"Bearer": []}],
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a notification"""
        notification = self.get_object()
        notification.delete()
        return api_response(
            message="Notification deleted successfully", status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        operation_id="delete_all_read",
        operation_summary="Delete all read notifications",
        operation_description="Delete all read notifications for the current user",
        tags=["Notifications"],
        responses={204: "No content"},
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["delete"])
    def delete_all_read(self, request):
        """Delete all read notifications"""
        queryset = self.get_queryset().filter(is_read=True)
        queryset.delete()
        return api_response(message="All read notifications deleted successfully")


class NotificationPreferenceViewSet(
    ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet
):
    """API endpoints for managing notification preferences"""

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    http_method_names = ["get", "put", "patch", "options"]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        """Return notification preferences for the current user"""
        user = self.request.user
        if user.role == "admin" and "user_id" in self.request.query_params:
            user_id = self.request.query_params.get("user_id")
            return NotificationPreference.objects.filter(user_id=user_id)
        return NotificationPreference.objects.filter(user=user)

    @swagger_auto_schema(
        operation_id="get_notification_preferences",
        operation_summary="Get notification preferences",
        operation_description="Get notification preferences for the current user",
        tags=["Notification Preferences"],
        responses={200: NotificationPreferenceSerializer, 404: "Not found"},
        security=[{"Bearer": []}],
    )
    def list(self, request, *args, **kwargs):
        """Get or create notification preferences for the current user"""
        user = request.user

        preference, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={"preferred_channels": ["in_app"]},
        )

        serializer = self.get_serializer(preference)
        return api_response(
            data=serializer.data,
            message="Notification preferences retrieved successfully",
        )

    @swagger_auto_schema(
        operation_id="update_notification_preferences",
        operation_summary="Update notification preferences",
        operation_description="Update notification preferences for the current user",
        tags=["Notification Preferences"],
        responses={200: NotificationPreferenceSerializer, 400: "Bad request"},
        security=[{"Bearer": []}],
    )
    def update(self, request, *args, **kwargs):
        """Update notification preferences"""
        partial = kwargs.pop("partial", False)

        user = request.user
        preference, created = NotificationPreference.objects.get_or_create(user=user)

        serializer = self.get_serializer(preference, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return api_response(
            data=serializer.data,
            message="Notification preferences updated successfully",
        )

    @swagger_auto_schema(
        operation_id="update_notification_channels",
        operation_summary="Update notification channels",
        operation_description="Update preferred notification delivery channels",
        tags=["Notification Preferences"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "channels": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_STRING,
                        enum=["in_app"],
                    ),
                    description="List of preferred notification channels",
                )
            },
            required=["channels"],
        ),
        responses={200: NotificationPreferenceSerializer, 400: "Bad request"},
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["patch"])
    def update_channels(self, request):
        """Update preferred notification channels"""
        channels = request.data.get("channels")

        if not channels or not isinstance(channels, list):
            return api_response(
                success=False,
                message="A list of notification channels is required",
                status=status.HTTP_400_BAD_REQUEST,
                errors={"channels": ["A list of notification channels is required"]},
            )

        valid_channels = [c[0] for c in NotificationPreference.CHANNEL_CHOICES]
        for channel in channels:
            if channel not in valid_channels:
                return api_response(
                    success=False,
                    message=f"Invalid channel '{channel}'",
                    status=status.HTTP_400_BAD_REQUEST,
                    errors={
                        "channels": [
                            f"Invalid channel '{channel}'. Valid options are: {', '.join(valid_channels)}."
                        ]
                    },
                )

        user = request.user
        preference, created = NotificationPreference.objects.get_or_create(user=user)
        preference.preferred_channels = channels
        preference.save()

        serializer = self.get_serializer(preference)
        return api_response(
            data=serializer.data, message="Notification channels updated successfully"
        )
