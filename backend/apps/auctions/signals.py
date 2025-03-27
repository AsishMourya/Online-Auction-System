from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import Auction, Bid, AuctionWatch


@receiver(post_save, sender=Auction)
def handle_auction_creation(sender, instance, created, **kwargs):
    """Handle specialized operations for auction creation"""
    if created:
        # Special operations for newly created auctions that aren't handled by triggers
        pass


# Disable the bid time extension signal since it's now handled by a trigger
# @receiver(post_save, sender=Bid)
# def handle_bid_time_extension(sender, instance, created, **kwargs):
#     """Extend auction time if a bid is placed near the end"""
#     if created:
#         auction = instance.auction
#
#         now = timezone.now()
#         time_remaining = (auction.end_time - now).total_seconds()
#
#         if (
#             auction.status == Auction.STATUS_ACTIVE and time_remaining < 300
#         ):  # 5 minutes in seconds
#             auction.end_time = now + timezone.timedelta(minutes=5)
#             auction.save(update_fields=["end_time"])


@receiver(post_save, sender=Bid)
def handle_bid_status_updates(sender, instance, created, **kwargs):
    """Handle bid status updates when a new bid is created"""
    if created and instance.status == Bid.STATUS_ACTIVE:
        Bid.objects.filter(auction=instance.auction, status=Bid.STATUS_ACTIVE).exclude(
            id=instance.id
        ).update(status=Bid.STATUS_OUTBID)
