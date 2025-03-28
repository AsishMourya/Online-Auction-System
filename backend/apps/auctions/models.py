from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

from apps.accounts.models import User


class Category(models.Model):
    """Category model for auction items"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    """Item model representing products to be auctioned"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    image_urls = ArrayField(
        models.URLField(),
        blank=True,
        default=list,
        help_text=_("List of image URLs for the item"),
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="items"
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Weight in kg"),
    )
    dimensions = models.CharField(
        max_length=100, blank=True, null=True, help_text=_("Format: LxWxH in cm")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

    class Meta:
        ordering = ["-created_at"]


class Auction(models.Model):
    """Auction model for bidding on items"""

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_ENDED = "ended"
    STATUS_CANCELLED = "cancelled"
    STATUS_SOLD = "sold"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending Start"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ENDED, "Ended"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_SOLD, "Sold"),
    ]

    TYPE_STANDARD = "standard"
    TYPE_RESERVE = "reserve"
    TYPE_BUY_NOW_ONLY = "buy_now_only"

    TYPE_CHOICES = [
        (TYPE_STANDARD, "Standard Auction"),
        (TYPE_RESERVE, "Reserve Auction"),
        (TYPE_BUY_NOW_ONLY, "Buy Now Only"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="auction")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auctions")
    title = models.CharField(max_length=255)
    description = models.TextField()
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    min_bid_increment = models.DecimalField(
        max_digits=12, decimal_places=2, default=1.00,
        help_text=_("Minimum increment amount for bids")
    )
    reserve_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    buy_now_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    auction_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_STANDARD
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def clean(self):
        """Validate auction data"""
        errors = {}

        if self.seller != self.item.owner:
            errors["seller"] = _("Seller must be the owner of the item")

        if self.starting_price and self.starting_price <= 0:
            errors["starting_price"] = _("Starting price must be greater than zero")

        if self.reserve_price:
            if self.reserve_price <= 0:
                errors["reserve_price"] = _("Reserve price must be greater than zero")
            if self.reserve_price < self.starting_price:
                errors["reserve_price"] = _(
                    "Reserve price cannot be less than starting price"
                )

        if self.buy_now_price:
            if self.buy_now_price <= 0:
                errors["buy_now_price"] = _("Buy now price must be greater than zero")
            if self.reserve_price and self.buy_now_price <= self.reserve_price:
                errors["buy_now_price"] = _(
                    "Buy now price must be greater than reserve price"
                )
            elif not self.reserve_price and self.buy_now_price <= self.starting_price:
                errors["buy_now_price"] = _(
                    "Buy now price must be greater than starting price"
                )

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = _("End time must be after start time")

        if (
            self.start_time
            and self.start_time < timezone.now()
            and self.status == self.STATUS_DRAFT
        ):
            errors["start_time"] = _(
                "Start time cannot be in the past for a draft auction"
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()

        now = timezone.now()

        if self.pk is None or self.status == self.STATUS_DRAFT:
            if now >= self.start_time:
                if now > self.end_time:
                    self.status = self.STATUS_ENDED
                else:
                    self.status = self.STATUS_ACTIVE
            else:
                self.status = self.STATUS_PENDING

        elif self.status == self.STATUS_PENDING and now >= self.start_time:
            self.status = self.STATUS_ACTIVE
        elif self.status == self.STATUS_ACTIVE and now >= self.end_time:
            self.status = self.STATUS_ENDED

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-start_time"]

    @property
    def current_price(self):
        """Get the current highest bid price or starting price if no bids"""
        highest_bid = (
            self.bids.filter(status=Bid.STATUS_ACTIVE).order_by("-amount").first()
        )
        return highest_bid.amount if highest_bid else self.starting_price

    @property
    def highest_bidder(self):
        """Get the current highest bidder"""
        highest_bid = (
            self.bids.filter(status=Bid.STATUS_ACTIVE).order_by("-amount").first()
        )
        return highest_bid.bidder if highest_bid else None

    @property
    def total_bids(self):
        """Get the total number of bids"""
        return self.bids.count()

    @property
    def time_remaining(self):
        """Get the time remaining for the auction"""
        if self.status != self.STATUS_ACTIVE:
            return None

        now = timezone.now()
        if now > self.end_time:
            return None

        return self.end_time - now

    def is_active(self):
        """Check if the auction is active"""
        now = timezone.now()
        return (
            self.status == self.STATUS_ACTIVE
            and self.start_time <= now
            and self.end_time > now
        )

    def can_bid(self, user):
        """Check if a user can place a bid on this auction"""
        return user.is_authenticated and user != self.seller and self.is_active()


class Bid(models.Model):
    """Bid model for auction bids"""

    STATUS_ACTIVE = "active"
    STATUS_OUTBID = "outbid"
    STATUS_WON = "won"
    STATUS_LOST = "lost"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_OUTBID, "Outbid"),
        (STATUS_WON, "Won"),
        (STATUS_LOST, "Lost"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="bids")
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )

    def __str__(self):
        return f"{self.bidder.email} bid {self.amount} on {self.auction.title}"

    def clean(self):
        """Validate bid data"""
        errors = {}

        if self.bidder == self.auction.seller:
            errors["bidder"] = _("You cannot bid on your own auction")

        if not self.auction.is_active():
            errors["auction"] = _("Cannot bid on an inactive auction")

        from apps.accounts.models import Wallet

        wallet = Wallet.objects.get(user=self.bidder)
        if wallet.balance < self.amount:
            errors["amount"] = _("Insufficient funds in your wallet")

        highest_bid = (
            self.auction.bids.filter(status=Bid.STATUS_ACTIVE)
            .order_by("-amount")
            .first()
        )

        min_bid = highest_bid.amount + self.auction.min_bid_increment if highest_bid else self.auction.starting_price
        if self.amount < min_bid:
            if highest_bid:
                errors["amount"] = _(
                    "Bid must be at least %(min_bid)s higher than the current highest bid of %(amount)s"
                ) % {"min_bid": self.auction.min_bid_increment, "amount": highest_bid.amount}
            else:
                errors["amount"] = _(
                    "Bid must be at least %(min_bid)s higher than the starting price of %(amount)s"
                ) % {"min_bid": self.auction.min_bid_increment, "amount": self.auction.starting_price}

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()

        is_new = self.pk is None

        if is_new:
            result = super().save(*args, **kwargs)

            from apps.notifications.services import create_notification
            from apps.notifications.models import Notification

            create_notification(
                recipient=self.auction.seller,
                notification_type=Notification.TYPE_BID,
                title=f"New bid on your auction: {self.auction.title}",
                message=f"A bid of {self.amount} was placed by {self.bidder.email}",
                priority=Notification.PRIORITY_MEDIUM,
                related_object_id=self.auction.id,
                related_object_type="auction",
            )

        else:
            result = super().save(*args, **kwargs)

        return result

    class Meta:
        ordering = ["-timestamp"]


class AuctionWatch(models.Model):
    """Model for users watching auctions"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watched_auctions"
    )
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="watchers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "auction")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} is watching {self.auction.title}"


@receiver(post_save, sender=Auction)
def notify_on_auction_creation(sender, instance, created, **kwargs):
    """Send notification when a new auction is created"""
    if created:
        from apps.notifications.services import create_notification
        from apps.notifications.models import Notification

        create_notification(
            recipient=instance.seller,
            notification_type=Notification.TYPE_NEW_AUCTION,
            title="Your auction has been created",
            message=f"Your auction '{instance.title}' has been created and will start at {instance.start_time}.",
            priority=Notification.PRIORITY_MEDIUM,
            related_object_id=instance.id,
            related_object_type="auction",
        )
