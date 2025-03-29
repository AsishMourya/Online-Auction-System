from rest_framework import serializers
from .models import Transaction, TransactionLog, AutoBid
from apps.accounts.models import Wallet


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'transaction_type', 'amount', 
            'status', 'created_at', 'updated_at', 'description',
            'completed_at', 'reference'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


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
