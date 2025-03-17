from apps.accounts.models import User
from .models import Notification, NotificationPreference


def create_notification(recipient, notification_type, title, message, **kwargs):
    """
    Create a notification for a user

    Args:
        recipient: User object - the user to send the notification to
        notification_type: str - type of notification
        title: str - notification title
        message: str - notification message
        **kwargs: additional fields for the notification

    Returns:
        Notification object
    """
    priority = kwargs.get("priority", Notification.PRIORITY_MEDIUM)
    related_object_id = kwargs.get("related_object_id")
    related_object_type = kwargs.get("related_object_type")

    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        related_object_id=related_object_id,
        related_object_type=related_object_type,
    )

    try:
        preferences = NotificationPreference.objects.get(user=recipient)

        if (
            notification_type == Notification.TYPE_BID
            and not preferences.bid_notifications
        ):
            return None
        elif (
            notification_type == Notification.TYPE_OUTBID
            and not preferences.outbid_notifications
        ):
            return None
        elif (
            notification_type == Notification.TYPE_AUCTION_WON
            and not preferences.auction_won_notifications
        ):
            return None
        elif (
            notification_type == Notification.TYPE_AUCTION_ENDED
            and not preferences.auction_ended_notifications
        ):
            return None
        elif (
            notification_type == Notification.TYPE_PAYMENT
            and not preferences.payment_notifications
        ):
            return None
        elif (
            notification_type == Notification.TYPE_ADMIN
            and not preferences.admin_notifications
        ):
            return None
    except NotificationPreference.DoesNotExist:
        pass

    return notification


def send_outbid_notification(bid):
    """
    Send notification to the previous highest bidder that they've been outbid
    """
    auction = bid.auction

    outbid_bids = auction.bids.filter(
        status="outbid", timestamp__lt=bid.timestamp
    ).order_by("-timestamp")

    if not outbid_bids.exists():
        return

    outbid_bid = outbid_bids.first()
    outbid_user = outbid_bid.bidder

    notification_message = (
        f"Your bid of {outbid_bid.amount} on '{auction.title}' has been outbid. "
        f"The new highest bid is {bid.amount} by another user."
    )

    create_notification(
        recipient=outbid_user,
        notification_type=Notification.TYPE_OUTBID,
        title=f"You've been outbid on {auction.title}",
        message=notification_message,
        priority=Notification.PRIORITY_HIGH,
        related_object_id=auction.id,
        related_object_type="auction",
    )


def send_auction_won_notification(auction, winning_bid):
    """
    Send notification to the winner of an auction
    """
    if not winning_bid:
        return

    winner = winning_bid.bidder

    notification_message = (
        f"Congratulations! You won the auction for '{auction.title}' with a bid of {winning_bid.amount}. "
        f"Please proceed to checkout to complete your purchase."
    )

    create_notification(
        recipient=winner,
        notification_type=Notification.TYPE_AUCTION_WON,
        title=f"You won the auction for {auction.title}",
        message=notification_message,
        priority=Notification.PRIORITY_HIGH,
        related_object_id=auction.id,
        related_object_type="auction",
    )


def send_auction_ended_notification(auction):
    """
    Send notification to the seller that their auction has ended
    """
    seller = auction.seller

    has_bids = auction.bids.exists()
    highest_bid = (
        auction.bids.filter(status__in=["active", "won"]).order_by("-amount").first()
    )
    reserve_met = highest_bid and (
        not auction.reserve_price or highest_bid.amount >= auction.reserve_price
    )

    if has_bids and reserve_met:
        notification_message = (
            f"Your auction for '{auction.title}' has ended with a winning bid of {highest_bid.amount}. "
            f"The buyer will be notified to complete the payment."
        )
    elif has_bids:
        notification_message = (
            f"Your auction for '{auction.title}' has ended but the reserve price was not met. "
            f"The highest bid was {highest_bid.amount}."
        )
    else:
        notification_message = (
            f"Your auction for '{auction.title}' has ended with no bids."
        )

    create_notification(
        recipient=seller,
        notification_type=Notification.TYPE_AUCTION_ENDED,
        title=f"Your auction for {auction.title} has ended",
        message=notification_message,
        priority=Notification.PRIORITY_HIGH,
        related_object_id=auction.id,
        related_object_type="auction",
    )


def send_new_auction_notification(auction, category_followers=None):
    """
    Send notification to users who follow this category
    """
    if not category_followers:
        return

    for user in category_followers:
        if user == auction.seller:
            continue

        notification_message = (
            f"A new auction '{auction.title}' has been listed in a category you follow. "
            f"Starting price: {auction.starting_price}."
        )

        create_notification(
            recipient=user,
            notification_type=Notification.TYPE_NEW_AUCTION,
            title=f"New auction: {auction.title}",
            message=notification_message,
            priority=Notification.PRIORITY_MEDIUM,
            related_object_id=auction.id,
            related_object_type="auction",
        )


def send_auction_cancelled_notification(auction):
    """
    Send notification to all bidders that an auction was cancelled
    """

    bidders = set(auction.bids.values_list("bidder", flat=True))

    for bidder_id in bidders:
        try:
            bidder = User.objects.get(id=bidder_id)

            notification_message = (
                f"The auction '{auction.title}' you bid on has been cancelled by the seller or admin. "
                f"No charges have been applied."
            )

            create_notification(
                recipient=bidder,
                notification_type=Notification.TYPE_AUCTION_CANCELLED,
                title=f"Auction cancelled: {auction.title}",
                message=notification_message,
                priority=Notification.PRIORITY_HIGH,
                related_object_id=auction.id,
                related_object_type="auction",
            )
        except User.DoesNotExist:
            pass


def send_payment_notification(user, transaction, is_sender=True):
    """
    Send notification about a payment/transaction
    """
    if is_sender:
        title = "Payment Sent"
        message = (
            f"Your payment of {transaction.amount} for '{transaction.reference}' was processed successfully. "
            f"Transaction ID: {transaction.id}"
        )
    else:
        title = "Payment Received"
        message = (
            f"You received a payment of {transaction.amount} for '{transaction.reference}'. "
            f"Transaction ID: {transaction.id}"
        )

    create_notification(
        recipient=user,
        notification_type=Notification.TYPE_PAYMENT,
        title=title,
        message=message,
        priority=Notification.PRIORITY_HIGH,
        related_object_id=transaction.id,
        related_object_type="transaction",
    )
