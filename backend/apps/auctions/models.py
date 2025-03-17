from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
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
        (STATUS_PENDING, "Pending Approval"),
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
        if self.status == self.STATUS_ACTIVE:
            if now > self.end_time:
                self.status = self.STATUS_ENDED
            elif now < self.start_time:
                self.status = self.STATUS_PENDING

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

        highest_bid = (
            self.auction.bids.filter(status=Bid.STATUS_ACTIVE)
            .order_by("-amount")
            .first()
        )

        min_bid = highest_bid.amount if highest_bid else self.auction.starting_price
        if self.amount <= min_bid:
            if highest_bid:
                errors["amount"] = _(
                    "Bid must be higher than the current highest bid of %(amount)s"
                ) % {"amount": min_bid}
            else:
                errors["amount"] = _(
                    "Bid must be higher than the starting price of %(amount)s"
                ) % {"amount": min_bid}

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()

        if not self.pk:
            Bid.objects.filter(auction=self.auction, status=self.STATUS_ACTIVE).update(
                status=self.STATUS_OUTBID
            )

            if self.auction.buy_now_price and self.amount >= self.auction.buy_now_price:
                self.status = self.STATUS_WON
                self.auction.status = Auction.STATUS_SOLD
                self.auction.save()

        super().save(*args, **kwargs)

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
