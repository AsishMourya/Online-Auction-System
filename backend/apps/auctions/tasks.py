from celery import shared_task
from django.utils import timezone
from .models import Auction


@shared_task
def check_auctions_status():
    """
    Periodic task to check and update auction statuses based on time
    - Start pending auctions that have reached their start time
    - End active auctions that have reached their end time
    """
    now = timezone.now()

    pending_auctions = Auction.objects.filter(
        status=Auction.STATUS_PENDING, start_time__lte=now
    )

    for auction in pending_auctions:
        auction.status = Auction.STATUS_ACTIVE
        auction.save()

    ended_auctions = Auction.objects.filter(
        status=Auction.STATUS_ACTIVE, end_time__lte=now
    )

    for auction in ended_auctions:
        auction.status = Auction.STATUS_ENDED
        auction.save()

    return {"started": pending_auctions.count(), "ended": ended_auctions.count()}


@shared_task
def cleanup_stale_auctions():
    """
    Periodic task to clean up draft auctions that are older than 30 days
    """
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    stale_drafts = Auction.objects.filter(
        status=Auction.STATUS_DRAFT, created_at__lt=thirty_days_ago
    )

    count = stale_drafts.count()
    stale_drafts.delete()

    return {"cleaned_drafts": count}


@shared_task
def notify_ending_soon_auctions():
    """
    Notify watchers of auctions ending within 24 hours
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    now = timezone.now()
    end_threshold = now + timezone.timedelta(hours=24)

    ending_soon = Auction.objects.filter(
        status=Auction.STATUS_ACTIVE, end_time__gt=now, end_time__lte=end_threshold
    )

    notification_count = 0

    for auction in ending_soon:
        for watcher in auction.watchers.all():
            user = watcher.user

            create_notification(
                recipient=user,
                notification_type=Notification.TYPE_AUCTION_ENDED,
                title=f"Auction ending soon: {auction.title}",
                message=f"The auction '{auction.title}' you're watching is ending in less than 24 hours.",
                priority=Notification.PRIORITY_MEDIUM,
                related_object_id=auction.id,
                related_object_type="auction",
            )
            notification_count += 1

    return {"notifications_sent": notification_count}
