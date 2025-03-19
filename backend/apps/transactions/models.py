from django.db import models
from django.utils import timezone
import uuid

from apps.accounts.models import User, PaymentMethod


class Transaction(models.Model):
    """Model for financial transactions"""

    TYPE_DEPOSIT = "deposit"
    TYPE_WITHDRAWAL = "withdrawal"
    TYPE_PURCHASE = "purchase"
    TYPE_SALE = "sale"
    TYPE_FEE = "fee"
    TYPE_REFUND = "refund"
    TYPE_BID_HOLD = "bid_hold"
    TYPE_BID_RELEASE = "bid_release"

    TRANSACTION_TYPES = [
        (TYPE_DEPOSIT, "Deposit"),
        (TYPE_WITHDRAWAL, "Withdrawal"),
        (TYPE_PURCHASE, "Purchase"),
        (TYPE_SALE, "Sale"),
        (TYPE_FEE, "Platform Fee"),
        (TYPE_REFUND, "Refund"),
        (TYPE_BID_HOLD, "Bid Hold"),
        (TYPE_BID_RELEASE, "Bid Release"),
    ]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES, db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    payment_method = models.ForeignKey(
        PaymentMethod, null=True, blank=True, on_delete=models.SET_NULL
    )
    reference = models.CharField(max_length=255, null=True, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "transaction_type"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["reference_id"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class TransactionLog(models.Model):
    """Log for transaction status changes and operations"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="logs"
    )
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    status_before = models.CharField(max_length=20, null=True, blank=True)
    status_after = models.CharField(max_length=20, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} - {self.transaction_id} ({self.timestamp})"


class AutoBid(models.Model):
    """Model for automatic bidding settings"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="autobids")
    auction = models.ForeignKey(
        "auctions.Auction", on_delete=models.CASCADE, related_name="autobids"
    )
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    bid_increment = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1.0,
        help_text="Amount to increment each automatic bid by",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "auction")
        ordering = ["-created_at"]

    def __str__(self):
        return f"AutoBid by {self.user.email} on {self.auction.title} (max: {self.max_amount})"
