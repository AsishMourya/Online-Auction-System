from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid
import decimal

from apps.accounts.models import User, PaymentMethod


class Transaction(models.Model):
    """Model for tracking all financial transactions"""

    TYPE_BID_HOLD = "bid_hold"  # Hold funds when bid is placed
    TYPE_BID_RELEASE = "bid_release"  # Release held funds if outbid
    TYPE_PURCHASE = "purchase"  # Payment for won auction
    TYPE_SALE = "sale"  # Funds received from auction sale
    TYPE_REFUND = "refund"  # Refund to buyer
    TYPE_FEE = "fee"  # Platform fee
    TYPE_WITHDRAWAL = "withdrawal"  # Withdraw funds to external account
    TYPE_DEPOSIT = "deposit"  # Deposit funds from external account

    TRANSACTION_TYPES = [
        (TYPE_BID_HOLD, "Bid Hold"),
        (TYPE_BID_RELEASE, "Bid Release"),
        (TYPE_PURCHASE, "Purchase"),
        (TYPE_SALE, "Sale"),
        (TYPE_REFUND, "Refund"),
        (TYPE_FEE, "Platform Fee"),
        (TYPE_WITHDRAWAL, "Withdrawal"),
        (TYPE_DEPOSIT, "Deposit"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    reference = models.CharField(
        max_length=255, help_text="Description or reference for the transaction"
    )
    reference_id = models.UUIDField(
        null=True, blank=True, help_text="ID of related object (auction, bid, etc.)"
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    external_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="ID from payment processor"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} - {self.amount} - {self.user.email}"
        )

    def clean(self):
        """Validate transaction data"""
        errors = {}

        if self.amount <= 0:
            errors["amount"] = _("Amount must be greater than zero")

        if (
            self.transaction_type in [self.TYPE_WITHDRAWAL, self.TYPE_PURCHASE]
            and self.amount > self.user.account_balance
        ):
            errors["amount"] = _("Insufficient funds for this transaction")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class AccountBalance(models.Model):
    """Model to track user account balances"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    held_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )  # Funds on hold for active bids
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Account Balances"

    def __str__(self):
        return f"{self.user.email} - Available: {self.available_balance}, Pending: {self.pending_balance}"

    @property
    def total_balance(self):
        """Get the total balance including available, pending, and held funds"""
        return self.available_balance + self.pending_balance + self.held_balance


class TransactionLog(models.Model):
    """Detailed log of all transaction events"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="logs"
    )
    action = models.CharField(max_length=255, help_text="Action or event that occurred")
    status_before = models.CharField(max_length=20, null=True, blank=True)
    status_after = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Transaction Logs"

    def __str__(self):
        return f"Log {self.id} for Transaction {self.transaction.id}"


class Wallet(models.Model):
    """User wallet model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.user.email}: {self.balance}"

    def deposit(self, amount):
        """Add funds to wallet"""
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        """Remove funds from wallet if sufficient balance"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False

    def can_withdraw(self, amount):
        """Check if wallet has sufficient funds"""
        return self.balance >= amount


class AutoBid(models.Model):
    """Configuration for automatic bidding"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="autobids")
    auction = models.ForeignKey(
        "auctions.Auction", on_delete=models.CASCADE, related_name="autobids"
    )
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    bid_increment = models.DecimalField(max_digits=12, decimal_places=2, default=1.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "auction")

    def __str__(self):
        return f"AutoBid by {self.user.email} on {self.auction.title} (max: {self.max_amount})"
