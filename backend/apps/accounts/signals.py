from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Wallet
from apps.notifications.models import NotificationPreference


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create wallet automatically when a user is created"""
    if created:
        Wallet.objects.get_or_create(user=instance)

        NotificationPreference.objects.get_or_create(
            user=instance, defaults={"preferred_channels": ["in_app"]}
        )


@receiver(post_save, sender=Wallet)
def log_wallet_transaction(sender, instance, created, **kwargs):
    """Log wallet balance changes"""

    if hasattr(instance, "_skip_transaction_log") and instance._skip_transaction_log:
        return

    if created:
        return

    if (
        hasattr(instance, "_previous_balance")
        and instance._previous_balance != instance.balance
        and instance._previous_balance is not None
    ):
        from apps.transactions.models import TransactionLog, Transaction
        from django.utils import timezone
        import uuid

        difference = instance.balance - instance._previous_balance
        action = "deposit" if difference > 0 else "withdrawal"

        if not hasattr(instance, "_transaction") or instance._transaction is None:
            transaction = Transaction.objects.create(
                id=uuid.uuid4(),
                user=instance.user,
                transaction_type=action,
                amount=abs(difference),
                status="completed",
                reference=f"Wallet {action} (auto-logged)",
                created_at=timezone.now(),
                completed_at=timezone.now(),
            )

            transaction._from_wallet_signal = True

            TransactionLog.objects.create(
                transaction=transaction,
                action="processed wallet effect",
                details={
                    "user_id": str(instance.user.id),
                    "previous_balance": str(instance._previous_balance),
                    "new_balance": str(instance.balance),
                    "difference": str(abs(difference)),
                    "from_wallet_signal": True,
                },
            )

            from apps.transactions.services import process_payment_notification

            process_payment_notification(transaction)
