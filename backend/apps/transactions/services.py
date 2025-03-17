from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.shortcuts import get_object_or_404

from apps.accounts.models import PaymentMethod
from apps.auctions.models import Auction, Bid
from .models import Transaction, AccountBalance, TransactionLog


def process_deposit(user, amount, payment_method_id):
    """
    Process a deposit of funds to a user's account

    Args:
        user: User object - the user making the deposit
        amount: Decimal - amount to deposit
        payment_method_id: UUID - ID of the payment method to use

    Returns:
        Transaction object or None if failed
    """
    try:
        payment_method = get_object_or_404(
            PaymentMethod, id=payment_method_id, user=user
        )

        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            return None

        with transaction.atomic():
            tx = Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TYPE_DEPOSIT,
                amount=amount,
                status=Transaction.STATUS_PENDING,
                reference="Deposit to account",
                payment_method=payment_method,
            )

            tx.status = Transaction.STATUS_COMPLETED
            tx.completed_at = timezone.now()
            tx.save()

            TransactionLog.objects.create(
                transaction=tx,
                action="Deposit initiated",
                status_before=Transaction.STATUS_PENDING,
                status_after=Transaction.STATUS_COMPLETED,
                details={"payment_method": str(payment_method.id)},
            )

            balance, created = AccountBalance.objects.get_or_create(user=user)

            balance.available_balance += amount
            balance.save()

        return tx
    except Exception as e:
        print(f"Error processing deposit: {str(e)}")
        return None


def process_withdrawal(user, amount, payment_method_id):
    """
    Process a withdrawal of funds from a user's account

    Args:
        user: User object - the user making the withdrawal
        amount: Decimal - amount to withdraw
        payment_method_id: UUID - ID of the payment method to use

    Returns:
        Transaction object or None if failed
    """
    try:
        payment_method = get_object_or_404(
            PaymentMethod, id=payment_method_id, user=user
        )

        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            return None

        try:
            balance = AccountBalance.objects.get(user=user)
        except AccountBalance.DoesNotExist:
            balance = AccountBalance.objects.create(user=user)

        if balance.available_balance < amount:
            return None

        with transaction.atomic():
            tx = Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TYPE_WITHDRAWAL,
                amount=amount,
                status=Transaction.STATUS_PENDING,
                reference="Withdrawal from account",
                payment_method=payment_method,
            )

            tx.status = Transaction.STATUS_COMPLETED
            tx.completed_at = timezone.now()
            tx.save()

            TransactionLog.objects.create(
                transaction=tx,
                action="Withdrawal initiated",
                status_before=Transaction.STATUS_PENDING,
                status_after=Transaction.STATUS_COMPLETED,
                details={"payment_method": str(payment_method.id)},
            )

            balance.available_balance -= amount
            balance.save()

        return tx
    except Exception as e:
        print(f"Error processing withdrawal: {str(e)}")
        return None


def process_auction_purchase(bid_id):
    """
    Process a purchase transaction for a winning bid

    Args:
        bid_id: UUID - ID of the winning bid

    Returns:
        tuple(purchaser_transaction, seller_transaction) or None if failed
    """
    try:
        bid = get_object_or_404(Bid, id=bid_id, status=Bid.STATUS_WON)
        auction = bid.auction

        if auction.status != Auction.STATUS_SOLD:
            return None

        with transaction.atomic():
            purchase_tx = Transaction.objects.create(
                user=bid.bidder,
                transaction_type=Transaction.TYPE_PURCHASE,
                amount=bid.amount,
                status=Transaction.STATUS_COMPLETED,
                reference=f"Purchase of {auction.title}",
                reference_id=auction.id,
                completed_at=timezone.now(),
            )

            platform_fee = bid.amount * Decimal("0.05")
            net_seller_amount = bid.amount - platform_fee

            fee_tx = Transaction.objects.create(
                user=auction.seller,
                transaction_type=Transaction.TYPE_FEE,
                amount=platform_fee,
                status=Transaction.STATUS_COMPLETED,
                reference=f"Fee for auction {auction.title}",
                reference_id=auction.id,
                completed_at=timezone.now(),
            )

            sale_tx = Transaction.objects.create(
                user=auction.seller,
                transaction_type=Transaction.TYPE_SALE,
                amount=net_seller_amount,
                status=Transaction.STATUS_COMPLETED,
                reference=f"Sale of {auction.title}",
                reference_id=auction.id,
                completed_at=timezone.now(),
            )

            buyer_balance, _ = AccountBalance.objects.get_or_create(user=bid.bidder)
            buyer_balance.held_balance -= bid.amount
            buyer_balance.save()

            seller_balance, _ = AccountBalance.objects.get_or_create(
                user=auction.seller
            )
            seller_balance.available_balance += net_seller_amount
            seller_balance.save()

        return (purchase_tx, sale_tx)
    except Exception as e:
        print(f"Error processing auction purchase: {str(e)}")
        return None


def initiate_refund(transaction_id, amount=None, reason=None):
    """
    Initiate a refund for a transaction

    Args:
        transaction_id: UUID - ID of the transaction to refund
        amount: Decimal - amount to refund (defaults to full amount)
        reason: str - reason for the refund

    Returns:
        Transaction object for the refund or None if failed
    """
    try:
        original_tx = get_object_or_404(Transaction, id=transaction_id)

        if amount is None:
            amount = original_tx.amount
        else:
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))

        if amount > original_tx.amount:
            return None

        with transaction.atomic():
            refund_tx = Transaction.objects.create(
                user=original_tx.user,
                transaction_type=Transaction.TYPE_REFUND,
                amount=amount,
                status=Transaction.STATUS_PENDING,
                reference=f"Refund for {original_tx.reference}",
                reference_id=original_tx.id,
                payment_method=original_tx.payment_method,
            )

            refund_tx.status = Transaction.STATUS_COMPLETED
            refund_tx.completed_at = timezone.now()
            refund_tx.save()

            TransactionLog.objects.create(
                transaction=refund_tx,
                action="Refund initiated",
                status_before=Transaction.STATUS_PENDING,
                status_after=Transaction.STATUS_COMPLETED,
                details={
                    "original_transaction": str(original_tx.id),
                    "reason": reason or "No reason provided",
                },
            )

            balance, _ = AccountBalance.objects.get_or_create(user=original_tx.user)
            balance.available_balance += amount
            balance.save()

        return refund_tx
    except Exception as e:
        print(f"Error processing refund: {str(e)}")
        return None
