from django.db import models
from django.utils import timezone
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model  # Add this import

User = get_user_model()  # Add this line to define User

from apps.accounts.models import PaymentMethod


class Transaction(models.Model):
    """Model for financial transactions"""
    
    # Transaction type constants
    TYPE_DEPOSIT = 'deposit'
    TYPE_WITHDRAWAL = 'withdrawal'
    TYPE_PAYMENT = 'payment'
    TYPE_REFUND = 'refund'
    TYPE_FEE = 'fee'
    TYPE_PURCHASE = 'purchase'
    TYPE_SALE = 'sale'
    TYPE_BID_HOLD = 'bid_hold'
    TYPE_BID_RELEASE = 'bid_release'
    
    TRANSACTION_TYPES = (
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAWAL, 'Withdrawal'),
        (TYPE_PAYMENT, 'Payment'),
        (TYPE_REFUND, 'Refund'),
        (TYPE_FEE, 'Fee'),
        (TYPE_PURCHASE, 'Purchase'),
        (TYPE_SALE, 'Sale'),
        (TYPE_BID_HOLD, 'Bid Hold'),
        (TYPE_BID_RELEASE, 'Bid Release'),
    )
    
    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default=STATUS_PENDING, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    reference_id = models.UUIDField(blank=True, null=True)
    payment_method = models.ForeignKey('accounts.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.status}"
        
    def mark_completed(self):
        """Mark the transaction as completed and set completed_at timestamp"""
        from django.utils import timezone
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save()


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="autobids")
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
