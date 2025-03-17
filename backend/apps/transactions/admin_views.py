from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal

from apps.accounts.permissions import IsAdmin
from .models import Transaction, TransactionLog
from .serializers import (
    TransactionSerializer,
    TransactionLogSerializer,
)
from .services import initiate_refund


class AdminTransactionViewSet(viewsets.ModelViewSet):
    """Admin API for managing transactions"""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_id="admin_list_transactions",
        operation_summary="List all transactions (Admin)",
        operation_description="Admin access to list all transactions with filtering options",
        tags=["Admin - Transactions"],
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by user ID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
            ),
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
            openapi.Parameter(
                "start_date",
                openapi.IN_QUERY,
                description="Filter by start date",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
            ),
            openapi.Parameter(
                "end_date",
                openapi.IN_QUERY,
                description="Filter by end date",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset

        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user__id=user_id)

        transaction_type = request.query_params.get("transaction_type")
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

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
        operation_id="admin_retrieve_transaction",
        operation_summary="Get transaction details (Admin)",
        operation_description="Admin access to get detailed transaction information",
        tags=["Admin - Transactions"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        logs = TransactionLog.objects.filter(transaction=instance).order_by("timestamp")
        log_serializer = TransactionLogSerializer(logs, many=True)

        return Response(
            {
                "message": "Transaction details retrieved successfully",
                "transaction": serializer.data,
                "logs": log_serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="admin_update_transaction_status",
        operation_summary="Update transaction status (Admin)",
        operation_description="Admin can update a transaction's status",
        tags=["Admin - Transactions"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="New status",
                    enum=["pending", "completed", "failed", "cancelled"],
                ),
                "notes": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Admin notes about the status change",
                ),
            },
            required=["status"],
        ),
        responses={200: TransactionSerializer, 400: "Bad Request"},
    )
    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update a transaction's status"""
        transaction = self.get_object()
        new_status = request.data.get("status")
        notes = request.data.get("notes", "")

        if new_status not in dict(Transaction.STATUS_CHOICES):
            return Response(
                {
                    "detail": f"Invalid status. Choices are: {', '.join(dict(Transaction.STATUS_CHOICES).keys())}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = transaction.status

        transaction.status = new_status
        if new_status == Transaction.STATUS_COMPLETED and not transaction.completed_at:
            transaction.completed_at = timezone.now()
        transaction.save()

        TransactionLog.objects.create(
            transaction=transaction,
            action="Status updated by admin",
            status_before=old_status,
            status_after=new_status,
            details={"admin": request.user.email, "notes": notes},
        )

        serializer = self.get_serializer(transaction)
        return Response(
            {
                "message": "Transaction status updated successfully",
                "transaction": serializer.data,
            }
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_transaction_stats",
    operation_summary="Transaction statistics (Admin)",
    operation_description="Get transaction statistics for admin dashboard",
    tags=["Admin - Transactions"],
    responses={200: "Transaction statistics"},
)
def admin_transaction_stats(request):
    """Admin dashboard with transaction statistics"""

    today = timezone.now().date()
    last_30_days = today - timezone.timedelta(days=30)

    total_transactions = Transaction.objects.count()
    total_volume = (
        Transaction.objects.filter(status=Transaction.STATUS_COMPLETED).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    transactions_by_type = Transaction.objects.values("transaction_type").annotate(
        count=Count("id")
    )

    volume_by_type = (
        Transaction.objects.filter(status=Transaction.STATUS_COMPLETED)
        .values("transaction_type")
        .annotate(total=Sum("amount"))
    )

    recent_transactions = Transaction.objects.order_by("-created_at")[:10]
    recent_data = TransactionSerializer(recent_transactions, many=True).data

    today_transactions = Transaction.objects.filter(created_at__date=today)
    today_count = today_transactions.count()
    today_volume = (
        today_transactions.filter(status=Transaction.STATUS_COMPLETED).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    month_transactions = Transaction.objects.filter(created_at__date__gte=last_30_days)
    month_count = month_transactions.count()
    month_volume = (
        month_transactions.filter(status=Transaction.STATUS_COMPLETED).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    return Response(
        {
            "overall_stats": {
                "total_transactions": total_transactions,
                "total_volume": total_volume,
            },
            "transactions_by_type": list(transactions_by_type),
            "volume_by_type": list(volume_by_type),
            "today_stats": {
                "transactions": today_count,
                "volume": today_volume,
            },
            "month_stats": {
                "transactions": month_count,
                "volume": month_volume,
            },
            "recent_transactions": recent_data,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_process_refund",
    operation_summary="Process refund (Admin)",
    operation_description="Process a refund for a transaction",
    tags=["Admin - Transactions"],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "transaction_id": openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                description="ID of the transaction to refund",
            ),
            "amount": openapi.Schema(
                type=openapi.TYPE_NUMBER,
                description="Amount to refund (optional, defaults to full amount)",
            ),
            "reason": openapi.Schema(
                type=openapi.TYPE_STRING, description="Reason for the refund"
            ),
        },
        required=["transaction_id", "reason"],
    ),
    responses={
        200: TransactionSerializer,
        400: "Bad Request",
        404: "Transaction not found",
    },
)
def admin_process_refund(request):
    """Admin endpoint to process a refund"""
    transaction_id = request.data.get("transaction_id")
    amount = request.data.get("amount")
    reason = request.data.get("reason")

    if not transaction_id:
        return Response(
            {"detail": "Transaction ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not reason:
        return Response(
            {"detail": "Reason for refund is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if amount:
        try:
            amount = Decimal(str(amount))
        except:
            return Response(
                {"detail": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST
            )

    refund_tx = initiate_refund(transaction_id, amount, reason)

    if refund_tx:
        TransactionLog.objects.create(
            transaction=refund_tx,
            action="Refund processed by admin",
            status_before=Transaction.STATUS_PENDING,
            status_after=refund_tx.status,
            details={
                "admin": request.user.email,
                "reason": reason,
                "original_transaction": str(transaction_id),
            },
        )

        serializer = TransactionSerializer(refund_tx)
        return Response(
            {"message": "Refund processed successfully", "transaction": serializer.data}
        )
    else:
        return Response(
            {"detail": "Failed to process refund."}, status=status.HTTP_400_BAD_REQUEST
        )
