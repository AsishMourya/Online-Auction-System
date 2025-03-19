from rest_framework import serializers
from .models import Transaction, TransactionLog, AutoBid
from apps.accounts.models import Wallet


class TransactionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_method_display = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "user_email",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "status",
            "status_display",
            "reference",
            "reference_id",
            "payment_method",
            "payment_method_display",
            "external_id",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "transaction_type_display",
            "status_display",
            "payment_method_display",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def get_payment_method_display(self, obj):
        if obj.payment_method:
            return f"{obj.payment_method.get_payment_type_display()} - {obj.payment_method.account_identifier}"
        return None


class TransactionLogSerializer(serializers.ModelSerializer):
    transaction_reference = serializers.CharField(
        source="transaction.reference", read_only=True
    )

    class Meta:
        model = TransactionLog
        fields = [
            "id",
            "transaction",
            "transaction_reference",
            "action",
            "status_before",
            "status_after",
            "timestamp",
            "details",
        ]
        read_only_fields = ["id", "transaction_reference", "timestamp"]


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    total_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="balance", read_only=True
    )

    class Meta:
        model = Wallet
        fields = [
            "id",
            "user",
            "user_email",
            "available_balance",
            "pending_balance",
            "held_balance",
            "total_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_email",
            "available_balance",
            "pending_balance",
            "held_balance",
            "total_balance",
            "created_at",
            "updated_at",
        ]
        ref_name = "TransactionWalletSerializer"


class AutoBidSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)

    class Meta:
        model = AutoBid
        fields = [
            "id",
            "user",
            "user_email",
            "auction",
            "auction_title",
            "max_amount",
            "bid_increment",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "user_email", "created_at", "updated_at"]
