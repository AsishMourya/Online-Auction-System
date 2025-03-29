from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.models import Wallet
from .models import Transaction
from .serializers import TransactionSerializer
from apps.accounts.serializers import WalletSerializer
from apps.core.mixins import SwaggerSchemaMixin, ApiResponseMixin
from apps.core.responses import api_response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deposit_funds(request):
    """Process a wallet deposit"""
    try:
        # Debug the incoming request
        print("Deposit request data:", request.data)
        
        # Get amount from request with better error handling
        try:
            amount_raw = request.data.get('amount')
            amount = Decimal(str(amount_raw))
            print(f"Parsed amount '{amount_raw}' to Decimal: {amount}")
        except (TypeError, ValueError) as e:
            print(f"Error parsing amount: {e}")
            return Response({
                'success': False,
                'message': f'Invalid amount value: {amount_raw}. Error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if amount <= 0:
            return Response({
                'success': False, 
                'message': 'Amount must be greater than zero'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use a transaction to ensure both operations succeed or fail together
        with transaction.atomic():
            # Get or create wallet with defaults for required fields
            wallet, _ = Wallet.objects.get_or_create(
                user=request.user,
                defaults={
                    'balance': 0,
                    'held_balance': 0,
                    'pending_balance': 0
                }
            )
            
            # Update wallet balance directly
            old_balance = wallet.balance
            wallet.balance += amount
            wallet.save()
            
            # Use constants from the Transaction model
            from .models import Transaction
            
            # Create transaction record with fields that exist in your model
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TYPE_DEPOSIT,  # Use constant
                amount=amount,
                status=Transaction.STATUS_COMPLETED,  # Use constant
                description=f"Wallet deposit of ${amount}",
                completed_at=timezone.now()
            )
            
            # Return response with transaction and updated wallet data
            return Response({
                'success': True,
                'message': f'Successfully deposited ${amount} to your wallet',
                'transaction': TransactionSerializer(transaction_obj).data,
                'wallet': {
                    'id': str(wallet.id),
                    'balance': float(wallet.balance),
                    'previous_balance': float(old_balance),
                    'updated_at': wallet.updated_at.isoformat() if hasattr(wallet, 'updated_at') else None
                }
            })
    except Exception as e:
        import traceback
        print(f"Error processing deposit: {str(e)}")
        print(traceback.format_exc())
        return Response({
            'success': False,
            'message': f'Error processing deposit: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def quick_deposit(request):
    """Quick deposit for development/debugging"""
    try:
        # Debug the incoming request
        print("Quick deposit request data:", request.data)
        
        # Get amount from request with better error handling
        try:
            amount_raw = request.data.get('amount', 10)
            amount = Decimal(str(amount_raw))
            print(f"Parsed amount '{amount_raw}' to: {amount}")
        except (TypeError, ValueError) as e:
            print(f"Error parsing amount: {e}")
            return Response({
                'success': False,
                'message': f'Invalid amount value: {amount_raw}. Error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use a transaction to ensure both operations succeed or fail together
        with transaction.atomic():
            # Get or create wallet with defaults for required fields
            wallet, _ = Wallet.objects.get_or_create(
                user=request.user,
                defaults={
                    'balance': 0,
                    'held_balance': 0,
                    'pending_balance': 0
                }
            )
            
            # Update wallet balance directly
            old_balance = wallet.balance
            wallet.balance += amount
            wallet.save()
            
            # Create transaction record with fields that exist in your model
            # Use the constants from the Transaction model
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TYPE_DEPOSIT,  # Use constant
                amount=amount,
                status=Transaction.STATUS_COMPLETED,  # Use constant
                description=f"Quick deposit of ${amount}",
                completed_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': f'Successfully added ${amount} to your wallet',
                'transaction': TransactionSerializer(transaction_obj).data,
                'wallet': {
                    'id': str(wallet.id),
                    'balance': float(wallet.balance),
                    'previous_balance': float(old_balance),
                    'updated_at': wallet.updated_at.isoformat() if hasattr(wallet, 'updated_at') else None
                }
            })
    except Exception as e:
        import traceback
        print(f"Error processing quick deposit: {str(e)}")
        print(traceback.format_exc())
        return Response({
            'success': False,
            'message': f'Error processing quick deposit: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


class TransactionViewSet(viewsets.ModelViewSet):
    """API endpoint for transaction management"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get transactions for the current user only"""
        user = self.request.user
        return Transaction.objects.filter(user=user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Override list method to add success field"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_id="get_account_balance",
    operation_summary="Get wallet balance",
    operation_description="Get current wallet balance for the user",
    tags=["Wallet"],
    responses={200: WalletSerializer, 404: "Wallet not found"},
)
def get_account_balance(request):
    """Get current wallet balance for the user"""
    try:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
    except Exception as e:
        return api_response(
            success=False,
            message=f"Error retrieving wallet: {str(e)}",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    serializer = WalletSerializer(wallet)
    return api_response(
        data={"wallet": serializer.data},
        message="Wallet balance retrieved successfully",
    )


class WalletViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
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

        return api_response(
            data={"wallet": serializer.data},
            message="Wallet retrieved successfully"
            if not created
            else "Wallet created successfully",
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
            return api_response(
                success=False,
                message="Amount must be greater than zero",
                status=status.HTTP_400_BAD_REQUEST,
                errors={"amount": ["Amount must be greater than zero"]},
            )

        transaction = process_deposit(request.user, amount, payment_method_id)

        if transaction:
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.deposit(Decimal(str(amount)))

            serializer = self.get_serializer(wallet)
            return api_response(
                data={"wallet": serializer.data},
                message="Wallet topped up successfully",
            )
        else:
            return api_response(
                success=False,
                message="Failed to process top-up",
                status=status.HTTP_400_BAD_REQUEST,
                errors={"detail": "Failed to process top-up"},
            )


# Add this function to process deposits
def process_deposit(user, amount, payment_method_id=None):
    """Process a deposit transaction"""
    try:
        # Convert amount to Decimal for consistency
        amount = Decimal(str(amount))
        
        # Create the transaction record
        transaction = Transaction.objects.create(
            user=user,
            transaction_type='deposit',
            amount=amount,
            status='completed',
            description=f"Wallet deposit of ${amount}",
            completed_at=timezone.now()
        )
        
        # Get or create the user's wallet
        wallet, _ = Wallet.objects.get_or_create(user=user)
        
        # Update wallet balance 
        wallet.balance += amount
        wallet.save()
        
        return transaction
    except Exception as e:
        print(f"Error processing deposit: {str(e)}")
        return None
