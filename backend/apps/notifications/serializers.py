from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    recipient_id = serializers.UUIDField(source="recipient.id", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_id",
            "recipient_email",
            "notification_type",
            "title",
            "message",
            "related_object_id",
            "related_object_type",
            "is_read",
            "priority",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "recipient_id",
            "recipient_email",
            "notification_type",
            "title",
            "message",
            "related_object_id",
            "related_object_type",
            "priority",
            "created_at",
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user_id",
            "user_email",
            "bid_notifications",
            "outbid_notifications",
            "auction_won_notifications",
            "auction_ended_notifications",
            "payment_notifications",
            "admin_notifications",
            "preferred_channels",
        ]
        read_only_fields = ["id", "user_id", "user_email"]
