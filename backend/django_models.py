from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone


# User Manager for Django Auth
class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(
            email=self.normalize_email(email), username=username, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, username, password, **extra_fields)


# User Model
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

    class Meta:
        db_table = "user"


# Role Model
class Role(models.Model):
    ADMIN = "Admin"
    SELLER = "Seller"
    BUYER = "Buyer"
    MODERATOR = "Moderator"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (SELLER, "Seller"),
        (BUYER, "Buyer"),
        (MODERATOR, "Moderator"),
    ]

    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True, choices=ROLE_CHOICES)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.role_name

    class Meta:
        db_table = "role"


# UserRole Model
class UserRole(models.Model):
    user_role_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_role"
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.username} - {self.role.role_name}"


# Category Model
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


# Item Model
class Item(models.Model):
    class Condition(models.TextChoices):
        NEW = "New", "New"
        USED = "Used", "Used"
        REFURBISHED = "Refurbished", "Refurbished"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"
        SOLD = "Sold", "Sold"

    item_id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="selling_items"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.RESTRICT)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_items",
    )
    reject_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "item"

    def __str__(self):
        return self.title


# ItemImage Model
class ItemImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image_url = models.CharField(max_length=1000)
    is_primary = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "item_image"
        constraints = [
            models.UniqueConstraint(
                fields=["item"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image",
            )
        ]

    def __str__(self):
        return f"Image for {self.item.title}"


# Auction Model
class Auction(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "Upcoming", "Upcoming"
        ACTIVE = "Active", "Active"
        ENDED = "Ended", "Ended"
        CANCELLED = "Cancelled", "Cancelled"

    auction_id = models.AutoField(primary_key=True)
    item = models.OneToOneField(Item, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    starting_bid = models.DecimalField(max_digits=15, decimal_places=2)
    reserve_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    bid_increment = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPCOMING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    extended_count = models.IntegerField(default=0)
    last_extended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auction"

    def __str__(self):
        return f"Auction for {self.item.title}"


# AuctionHistory Model
class AuctionHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "Created", "Created"
        STARTED = "Started", "Started"
        EXTENDED = "Extended", "Extended"
        ENDED = "Ended", "Ended"
        CANCELLED = "Cancelled", "Cancelled"

    history_id = models.AutoField(primary_key=True)
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="history"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = "auction_history"
        verbose_name_plural = "auction histories"

    def __str__(self):
        return f"{self.action} - Auction #{self.auction.auction_id}"


# Bid Model
class Bid(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        OUTBID = "Outbid", "Outbid"
        WON = "Won", "Won"

    bid_id = models.AutoField(primary_key=True)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="bids")
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    bid_amount = models.DecimalField(max_digits=15, decimal_places=2)
    bid_time = models.DateTimeField(auto_now_add=True)
    is_auto_bid = models.BooleanField(default=False)
    max_auto_bid_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    bid_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        db_table = "bid"

    def __str__(self):
        return (
            f"${self.bid_amount} by {self.bidder.username} on {self.auction.item.title}"
        )


# PaymentMethod Model
class PaymentMethod(models.Model):
    class PaymentType(models.TextChoices):
        CREDIT_CARD = "Credit Card", "Credit Card"
        PAYPAL = "PayPal", "PayPal"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        CRYPTOCURRENCY = "Cryptocurrency", "Cryptocurrency"

    payment_method_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_methods"
    )
    payment_type = models.CharField(max_length=50, choices=PaymentType.choices)
    account_number = models.CharField(
        max_length=255
    )  # Should be encrypted in application code
    expiry_date = models.DateField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_method"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_payment",
            )
        ]

    def __str__(self):
        return f"{self.payment_type} for {self.user.username}"


# ShippingAddress Model
class ShippingAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shipping_addresses"
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shipping_address"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address",
            )
        ]

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.country} for {self.user.username}"


# Transaction Model
class Transaction(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"
        REFUNDED = "Refunded", "Refunded"

    class ShippingStatus(models.TextChoices):
        NOT_SHIPPED = "Not Shipped", "Not Shipped"
        SHIPPED = "Shipped", "Shipped"
        DELIVERED = "Delivered", "Delivered"

    transaction_id = models.AutoField(primary_key=True)
    auction = models.OneToOneField(Auction, on_delete=models.RESTRICT)
    seller = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="sold_transactions"
    )
    buyer = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="bought_transactions"
    )
    final_amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    shipping_status = models.CharField(
        max_length=20,
        choices=ShippingStatus.choices,
        default=ShippingStatus.NOT_SHIPPED,
    )
    tracking_number = models.CharField(max_length=100, blank=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True
    )
    shipping_address = models.ForeignKey(
        ShippingAddress, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        db_table = "transaction"

    def __str__(self):
        return (
            f"Transaction #{self.transaction_id} for Auction #{self.auction.auction_id}"
        )


# Feedback Model
class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="feedback"
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews_given"
    )
    reviewee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews_received"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feedback"
        unique_together = ("transaction", "reviewer")

    def __str__(self):
        return f"Rating {self.rating}/5 by {self.reviewer.username}"


# Notification Model
class Notification(models.Model):
    class Type(models.TextChoices):
        OUTBID = "Outbid", "Outbid"
        AUCTION_ENDED = "AuctionEnded", "Auction Ended"
        ITEM_SOLD = "ItemSold", "Item Sold"
        BID_WON = "BidWon", "Bid Won"
        ITEM_APPROVED = "ItemApproved", "Item Approved"
        ITEM_REJECTED = "ItemRejected", "Item Rejected"
        PAYMENT_RECEIVED = "PaymentReceived", "Payment Received"
        PAYMENT_FAILED = "PaymentFailed", "Payment Failed"
        ITEM_SHIPPED = "ItemShipped", "Item Shipped"

    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    related_auction = models.ForeignKey(
        Auction, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_item = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_bid = models.ForeignKey(
        Bid, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "notification"

    def __str__(self):
        return f"{self.type} notification for {self.user.username}"


# Watchlist Model
class Watchlist(models.Model):
    watchlist_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="watchers"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "watchlist"
        unique_together = ("user", "auction")

    def __str__(self):
        return f"{self.user.username} watching {self.auction.item.title}"


# AuditLog Model
class AuditLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    table_affected = models.CharField(max_length=100)
    record_id = models.IntegerField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "audit_log"

    def __str__(self):
        return f"{self.action} on {self.table_affected} #{self.record_id}"
