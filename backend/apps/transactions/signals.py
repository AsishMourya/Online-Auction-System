from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Transaction, TransactionLog
from apps.accounts.models import Wallet
from .services import process_payment_notification


@receiver(pre_save, sender=Transaction)
def log_transaction_changes(sender, instance, **kwargs):
    """Log changes to transaction status"""
    if instance.pk:
        try:
            old_instance = Transaction.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                TransactionLog.objects.create(
                    transaction=instance,
                    action=f"Status changed from {old_instance.status} to {instance.status}",
                    status_before=old_instance.status,
                    status_after=instance.status,
                    details={"updated_by": "system"},
                )

                if (
                    instance.status == Transaction.STATUS_COMPLETED
                    and not instance.completed_at
                ):
                    instance.completed_at = timezone.now()
        except Transaction.DoesNotExist:
            pass


@receiver(post_save, sender=Transaction)
def process_transaction_effects(sender, instance, created, **kwargs):
    """Process effects of transactions on wallet"""

    if hasattr(instance, "_from_wallet_signal") and instance._from_wallet_signal:
        return

    if (
        not hasattr(instance, "_being_processed")
        and instance.status == Transaction.STATUS_COMPLETED
    ):
        instance._being_processed = True

        if TransactionLog.objects.filter(
            transaction=instance, action="processed wallet effect"
        ).exists():
            if not TransactionLog.objects.filter(
                transaction=instance, action="notification_sent"
            ).exists():
                process_payment_notification(instance)
            return

        wallet, _ = Wallet.objects.get_or_create(user=instance.user)

        wallet._skip_transaction_log = True
        wallet._transaction = instance
        wallet._previous_balance = wallet.balance

        if instance.transaction_type in [
            Transaction.TYPE_DEPOSIT,
            Transaction.TYPE_SALE,
            Transaction.TYPE_BID_RELEASE,
            Transaction.TYPE_REFUND,
        ]:
            wallet.balance += instance.amount
            wallet.save()

        elif instance.transaction_type in [
            Transaction.TYPE_WITHDRAWAL,
            Transaction.TYPE_FEE,
            Transaction.TYPE_BID_HOLD,
            Transaction.TYPE_PURCHASE,
        ]:
            wallet.balance = max(0, wallet.balance - instance.amount)
            wallet.save()

        if instance.transaction_type == Transaction.TYPE_BID_HOLD:
            wallet.held_balance += instance.amount
            wallet.save()

        elif instance.transaction_type == Transaction.TYPE_BID_RELEASE:
            wallet.held_balance = max(0, wallet.held_balance - instance.amount)
            wallet.save()

        TransactionLog.objects.create(
            transaction=instance,
            action="processed wallet effect",
            details={
                "processed_at": timezone.now().isoformat(),
                "wallet_id": str(wallet.id),
            },
        )

        process_payment_notification(instance)
