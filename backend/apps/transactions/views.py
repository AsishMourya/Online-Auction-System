from decimal import Decimal
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.core.mixins import SwaggerSchemaMixin

from .models import AccountBalance, Transaction, Wallet
from .serializers import (
    AccountBalanceSerializer,
    TransactionSerializer,
    WalletSerializer,
)
from .services import (
    process_deposit,
    process_withdrawal,
)


class TransactionViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for user's transaction history"""

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        user = self.request.user
        return Transaction.objects.filter(user=user).order_by("-created_at")

    @swagger_auto_schema(
        operation_id="list_transactions",
        operation_summary="List transactions",
        operation_description="Get all transactions for the current user",
        tags=["Transactions"],
        manual_parameters=[
            openapi.Parameter(
                "transaction_type",
                openapi.IN_QUERY,
                description="Filter by transaction type",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by status",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: TransactionSerializer(many=True)},
        security=[{"Bearer": []}],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        transaction_type = request.query_params.get("transaction_type")
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "Transactions retrieved successfully",
                "transactions": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="retrieve_transaction",
        operation_summary="Get transaction details",
        operation_description="Get details for a specific transaction",
        tags=["Transactions"],
        responses={200: TransactionSerializer, 404: "Not found"},
        security=[{"Bearer": []}],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Transaction details retrieved successfully",
                "transaction": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="deposit_funds",
        operation_summary="Deposit funds",
        operation_description="Deposit funds into user account",
        tags=["Transactions"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Amount to deposit"
                ),
                "payment_method_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description="Payment method to use",
                ),
            },
            required=["amount", "payment_method_id"],
        ),
        responses={
            200: TransactionSerializer,
            400: "Bad request",
            404: "Payment method not found",
        },
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["post"])
    def deposit(self, request):
        """Deposit funds to user account"""
        amount = request.data.get("amount")
        payment_method_id = request.data.get("payment_method_id")

        if not amount or float(amount) <= 0:
            return Response(
                {"detail": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction = process_deposit(request.user, amount, payment_method_id)

        if transaction:
            serializer = self.get_serializer(transaction)
            return Response(
                {
                    "message": "Deposit processed successfully",
                    "transaction": serializer.data,
                }
            )
        else:
            return Response(
                {"detail": "Failed to process deposit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        operation_id="withdraw_funds",
        operation_summary="Withdraw funds",
        operation_description="Withdraw funds from user account",
        tags=["Transactions"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Amount to withdraw"
                ),
                "payment_method_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description="Payment method to use for withdrawal",
                ),
            },
            required=["amount", "payment_method_id"],
        ),
        responses={
            200: TransactionSerializer,
            400: "Bad request",
            404: "Payment method not found",
        },
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["post"])
    def withdraw(self, request):
        """Withdraw funds from user account"""
        amount = request.data.get("amount")
        payment_method_id = request.data.get("payment_method_id")

        if not amount or float(amount) <= 0:
            return Response(
                {"detail": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction = process_withdrawal(request.user, amount, payment_method_id)

        if transaction:
            serializer = self.get_serializer(transaction)
            return Response(
                {
                    "message": "Withdrawal processed successfully",
                    "transaction": serializer.data,
                }
            )
        else:
            return Response(
                {"detail": "Failed to process withdrawal."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_id="get_account_balance",
    operation_summary="Get account balance",
    operation_description="Get current account balance for the user",
    tags=["Account"],
    responses={200: AccountBalanceSerializer, 404: "Account not found"},
)
def get_account_balance(request):
    """Get current account balance for the user"""
    try:
        balance = AccountBalance.objects.get(user=request.user)
    except AccountBalance.DoesNotExist:
        balance = AccountBalance.objects.create(user=request.user)

    serializer = AccountBalanceSerializer(balance)
    return Response(
        {
            "message": "Account balance retrieved successfully",
            "balance": serializer.data,
        }
    )


class WalletViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for user's wallet"""

    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        return Wallet.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_id="get_wallet",
        operation_summary="Get wallet",
        operation_description="Get wallet details for the current user or create one if it doesn't exist",
        tags=["Wallet"],
        responses={200: WalletSerializer},
        security=[{"Bearer": []}],
    )
    def list(self, request, *args, **kwargs):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)

        return Response(
            {
                "message": "Wallet retrieved successfully"
                if not created
                else "Wallet created successfully",
                "wallet": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="topup_wallet",
        operation_summary="Top-up wallet",
        operation_description="Add funds to user wallet",
        tags=["Wallet"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Amount to add to wallet"
                ),
                "payment_method_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description="Payment method to use",
                ),
            },
            required=["amount", "payment_method_id"],
        ),
        responses={
            200: WalletSerializer,
            400: "Bad request",
            404: "Payment method not found",
        },
        security=[{"Bearer": []}],
    )
    @action(detail=False, methods=["post"])
    def topup(self, request):
        """Add funds to user wallet"""
        amount = request.data.get("amount")
        payment_method_id = request.data.get("payment_method_id")

        if not amount or float(amount) <= 0:
            return Response(
                {"detail": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction = process_deposit(request.user, amount, payment_method_id)

        if transaction:
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.deposit(Decimal(str(amount)))

            serializer = self.get_serializer(wallet)
            return Response(
                {"message": "Wallet topped up successfully", "wallet": serializer.data}
            )
        else:
            return Response(
                {"detail": "Failed to process top-up."},
                status=status.HTTP_400_BAD_REQUEST,
            )
