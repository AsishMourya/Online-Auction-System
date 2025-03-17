from django.db import models
import uuid

from apps.accounts.models import User


class Notification(models.Model):
    """Base model for all notification types"""

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
    ]

    TYPE_BID = "bid"
    TYPE_OUTBID = "outbid"
    TYPE_AUCTION_WON = "auction_won"
    TYPE_AUCTION_ENDED = "auction_ended"
    TYPE_AUCTION_CANCELLED = "auction_cancelled"
    TYPE_AUCTION_STARTED = "auction_started"
    TYPE_NEW_AUCTION = "new_auction"
    TYPE_PAYMENT = "payment"
    TYPE_ADMIN = "admin"

    NOTIFICATION_TYPES = [
        (TYPE_BID, "New Bid"),
        (TYPE_OUTBID, "Outbid"),
        (TYPE_AUCTION_WON, "Auction Won"),
        (TYPE_AUCTION_ENDED, "Auction Ended"),
        (TYPE_AUCTION_CANCELLED, "Auction Cancelled"),
        (TYPE_AUCTION_STARTED, "Auction Started"),
        (TYPE_NEW_AUCTION, "New Auction"),
        (TYPE_PAYMENT, "Payment"),
        (TYPE_ADMIN, "Admin Message"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} (to {self.recipient.email})"


class NotificationPreference(models.Model):
    """User preferences for notification delivery"""

    IN_APP = "in_app"

    CHANNEL_CHOICES = [
        (IN_APP, "In-App Notification"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    bid_notifications = models.BooleanField(default=True)
    outbid_notifications = models.BooleanField(default=True)
    auction_won_notifications = models.BooleanField(default=True)
    auction_ended_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    admin_notifications = models.BooleanField(default=True)
    preferred_channels = models.JSONField(default=list)

    def __str__(self):
        return f"Notification preferences for {self.user.email}"

    @property
    def enabled_channels(self):
        """Get list of enabled notification channels"""
        if not self.preferred_channels:
            return [self.IN_APP, self.EMAIL]
        return self.preferred_channels
