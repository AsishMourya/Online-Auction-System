from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Transaction, TransactionLog, AccountBalance, Wallet
from apps.auctions.models import Bid, Auction


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
