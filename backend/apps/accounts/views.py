import decimal
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, viewsets
import random
import string
from django.db import transaction

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import jwt
from django.conf import settings

from apps.core.mixins import SwaggerSchemaMixin, ApiResponseMixin
from apps.core.responses import api_response

from .models import Address, PaymentMethod, Wallet
from .permissions import IsOwner
from .serializers import (
    AddressSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
    UserProfileBasicSerializer,
    UserRegistrationSerializer,
    WalletSerializer,
    UserLoginSerializer,
)

from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserPasswordChangeSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining JWT token pair
    """
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Log the token being returned (first 20 chars only)
        if 'access' in response.data:
            access_preview = response.data['access'][:20] + '...' if response.data['access'] else 'None'
            print(f"Generated access token: {access_preview}")
        
        # Wrap with success wrapper if needed
        if hasattr(settings, 'USE_RESPONSE_WRAPPER') and settings.USE_RESPONSE_WRAPPER:
            response.data = {
                'success': True,
                'data': response.data,
                'message': 'Login successful'
            }
        
        return response


class CustomTokenRefreshView(ApiResponseMixin, TokenRefreshView):
    @swagger_auto_schema(
        operation_summary="Refresh JWT token",
        operation_description="Get a new access token using refresh token",
        responses={
            200: "Token refreshed successfully",
            400: "Invalid or expired token",
            401: "Authentication Failed",
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)

            if not serializer.is_valid():
                return api_response(
                    success=False,
                    message="Token refresh failed",
                    errors=serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return api_response(
                data=serializer.validated_data, message="Token refreshed successfully"
            )
        except Exception as e:
            error_message = str(e)
            status_code = status.HTTP_400_BAD_REQUEST

            if "token is blacklisted" in error_message.lower():
                error_message = "Token has been blacklisted"
            elif "token is invalid or expired" in error_message.lower():
                error_message = "Token is invalid or expired"
                status_code = status.HTTP_401_UNAUTHORIZED

            return api_response(
                success=False,
                message="Token refresh failed",
                errors={"detail": error_message},
                status=status_code,
            )


class UserRegistrationView(ApiResponseMixin, generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]  # Allow anyone to register
    serializer_class = UserRegistrationSerializer
    
    @swagger_auto_schema(
        operation_summary="Register new user",
        operation_description="Create a new user account",
        responses={201: "User registered successfully"},
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            
            # Generate tokens for the user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Return success response with tokens
            return api_response(
                success=True,
                message="User registered successfully",
                data={
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                    "access": access_token,
                    "refresh": refresh_token,
                },
                status=status.HTTP_201_CREATED,
            )
        
        return api_response(
            success=False,
            message="Registration failed",
            errors=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserLoginView(ApiResponseMixin, generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer
    
    @swagger_auto_schema(
        operation_summary="User login",
        operation_description="Authenticate user and get tokens",
        responses={200: "Login successful"},
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return api_response(
                success=True,
                message="Login successful",
                data={
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                    "access": access_token,
                    "refresh": refresh_token,
                },
                status=status.HTTP_200_OK,
            )
        
        return api_response(
            success=False,
            message="Invalid credentials",
            errors=serializer.errors,
            status=status.HTTP_401_UNAUTHORIZED,
        )


class UserProfileViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    @swagger_auto_schema(
        operation_summary="Get user profile",
        operation_description="Get current user's profile details",
        responses={200: UserProfileSerializer},
        tags=["Users"],
    )
    def list(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return api_response(
            data=serializer.data, message="User profile retrieved successfully"
        )

    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Update current user's profile",
        responses={200: UserProfileSerializer},
        tags=["Users"],
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = request.user
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(
            data=serializer.data, message="Profile updated successfully"
        )

    @swagger_auto_schema(
        operation_summary="Change password",
        operation_description="Change user's password",
        request_body=UserPasswordChangeSerializer,
        responses={200: "Password changed successfully"},
        tags=["Users"],
    )
    @action(detail=False, methods=["post"])
    def change_password(self, request):
        user = request.user
        serializer = UserPasswordChangeSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            old_password = serializer.validated_data.get("old_password")
            new_password = serializer.validated_data.get("new_password")

            if not user.check_password(old_password):
                return api_response(
                    success=False,
                    message="Incorrect password",
                    errors={"old_password": ["Incorrect password"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(new_password)
            user.save()

            return api_response(message="Password changed successfully")

        return api_response(
            success=False,
            message="Password change failed",
            errors=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class AddressViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()
        return Address.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="List user addresses",
        operation_description="Get all addresses for current user",
        responses={200: AddressSerializer(many=True)},
        tags=["Addresses"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create address",
        operation_description="Add a new address for current user",
        responses={201: AddressSerializer},
        tags=["Addresses"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data["user"] = request.user

        is_default = serializer.validated_data.get("is_default", False)

        if not Address.objects.filter(user=request.user).exists():
            serializer.validated_data["is_default"] = True
        elif is_default:
            Address.objects.filter(user=request.user, is_default=True).update(
                is_default=False
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return api_response(
            data=serializer.data,
            message="Address added successfully",
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_summary="Set default address",
        operation_description="Set an address as default",
        responses={200: AddressSerializer},
        tags=["Addresses"],
    )
    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        address = self.get_object()

        Address.objects.filter(user=request.user, is_default=True).update(
            is_default=False
        )

        address.is_default = True
        address.save()

        serializer = self.get_serializer(address)
        return api_response(data=serializer.data, message="Address set as default")


class PaymentMethodViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()
        return PaymentMethod.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="List payment methods",
        operation_description="Get all payment methods for current user",
        responses={200: PaymentMethodSerializer(many=True)},
        tags=["Payment Methods"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create payment method",
        operation_description="Add a new payment method for current user - only name and type required",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Name for the payment method"
                ),
                "payment_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of payment method",
                    enum=["credit_card", "debit_card", "crypto", "bank"],
                ),
                "is_default": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Set as default payment method",
                    default=False,
                ),
            },
            required=["name", "payment_type"],
        ),
        responses={201: PaymentMethodSerializer},
        tags=["Payment Methods"],
    )
    def create(self, request, *args, **kwargs):
        name = request.data.get("name")
        payment_type = request.data.get("payment_type")
        is_default = request.data.get("is_default", False)

        provider = name
        account_identifier = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=12)
        )

        payment_data = {
            "payment_type": payment_type,
            "provider": provider,
            "account_identifier": account_identifier,
            "is_default": is_default,
        }

        serializer = self.get_serializer(data=payment_data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data["user"] = request.user

        if not PaymentMethod.objects.filter(user=request.user).exists():
            serializer.validated_data["is_default"] = True
        elif is_default:
            PaymentMethod.objects.filter(user=request.user, is_default=True).update(
                is_default=False
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return api_response(
            data=serializer.data,
            message="Payment method added successfully",
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class WalletViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for user's wallet"""

    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()
        return Wallet.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_id="get_wallet",
        operation_summary="Get wallet details",
        operation_description="Get detailed wallet information including balance breakdown and financial status",
        tags=["Wallet"],
        responses={200: WalletSerializer},
    )
    def list(self, request, *args, **kwargs):
        wallet = Wallet.objects.get(user=request.user)
        serializer = self.get_serializer(wallet)

        from apps.transactions.models import Transaction
        from apps.transactions.serializers import TransactionSerializer

        recent_transactions = Transaction.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:5]
        transaction_serializer = TransactionSerializer(recent_transactions, many=True)

        from apps.auctions.models import Bid
        from apps.auctions.serializers import BidSerializer

        active_bids = Bid.objects.filter(bidder=request.user, status=Bid.STATUS_ACTIVE)
        active_bids_serializer = BidSerializer(active_bids, many=True)

        from django.db.models import Sum

        total_spent = (
            Transaction.objects.filter(
                user=request.user, transaction_type="purchase", status="completed"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        total_earned = (
            Transaction.objects.filter(
                user=request.user, transaction_type="sale", status="completed"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        return api_response(
            data={
                "wallet": serializer.data,
                "financial_summary": {
                    "total_spent": total_spent,
                    "total_earned": total_earned,
                    "net_balance": total_earned - total_spent,
                },
                "recent_transactions": transaction_serializer.data,
                "active_bids": active_bids_serializer.data,
            },
            message="Wallet details retrieved successfully",
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
    )
    @action(detail=False, methods=["post"])
    def topup(self, request):
        """Add funds to user wallet"""
        from apps.transactions.models import Transaction, TransactionLog
        import uuid

        amount = request.data.get("amount")
        payment_method_id = request.data.get("payment_method_id")

        if not amount or float(amount) <= 0:
            return api_response(
                success=False,
                message="Amount must be greater than zero",
                status=status.HTTP_400_BAD_REQUEST,
                errors={"amount": ["Amount must be greater than zero"]},
            )

        try:
            with transaction.atomic():
                wallet = Wallet.objects.get(user=request.user)
                previous_balance = wallet.balance

                transaction_id = uuid.uuid4()

                if Transaction.objects.filter(id=transaction_id).exists():
                    transaction_id = uuid.uuid4()

                tx = Transaction.objects.create(
                    id=transaction_id,
                    user=request.user,
                    transaction_type="deposit",
                    amount=decimal.Decimal(str(amount)),
                    status="pending",
                    reference="Wallet deposit",
                )

                tx.status = "completed"
                tx.completed_at = timezone.now()
                tx.save()

            wallet.refresh_from_db()
            serializer = self.get_serializer(wallet)
            return api_response(
                data={"wallet": serializer.data, "transaction_id": str(tx.id)},
                message="Wallet topped up successfully",
            )
        except Exception as e:
            return api_response(
                success=False,
                message=f"Failed to process top-up: {str(e)}",
                status=status.HTTP_400_BAD_REQUEST,
                errors={"detail": f"Failed to process top-up: {str(e)}"},
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary="Log out",
    operation_description="Blacklist the refresh token to log user out",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "refresh": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Refresh token",
            )
        },
        required=["refresh"],
    ),
    responses={200: "Logged out successfully"},
    tags=["Authentication"],
)
def logout_view(request):
    try:
        refresh_token = request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return api_response(message="Logged out successfully")
    except Exception as e:
        return api_response(
            success=False,
            message="Logout failed",
            errors={"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary="Delete user account",
    operation_description="Permanently delete the authenticated user's account",
    responses={200: "Account deleted successfully"},
    tags=["Account Management"],
)
def delete_account(request):
    """Delete the authenticated user's account"""
    try:
        user = request.user
        
        # Delete user objects like auctions, bids, etc.
        # This depends on your model relationships and CASCADE settings
        
        # Finally delete the user
        user.delete()
        
        return api_response(message="Account deleted successfully")
    except Exception as e:
        return api_response(
            success=False,
            message="Failed to delete account",
            errors={"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow anyone to access this endpoint for debugging
def debug_auth(request):
    """Debug endpoint to inspect authentication details without requiring valid auth"""
    # Get all headers for debugging
    auth_header = request.META.get('HTTP_AUTHORIZATION', 'Not found')
    headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
    
    # Try to decode the token
    token_info = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        try:
            # Try to decode the token without verification (for debug only)
            decoded = jwt.decode(token, options={"verify_signature": False})
            token_info = {
                'decoded': decoded,
                'format_valid': True
            }
        except Exception as e:
            token_info = {
                'error': str(e),
                'format_valid': False
            }
    
    return Response({
        'is_authenticated': request.user.is_authenticated,
        'user': str(request.user),
        'auth_header': auth_header,
        'token_info': token_info,
        'all_headers': headers,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token(request):
    """Verify if a token is valid and return its contents"""
    token = request.data.get('token')
    
    if not token:
        return Response({
            'valid': False,
            'error': 'No token provided'
        }, status=400)
    
    try:
        # Try to parse the token
        access_token = AccessToken(token)
        
        # If successful, return the token contents
        return Response({
            'valid': True,
            'token_type': 'access',
            'payload': access_token.payload,
            'user_id': access_token.get('user_id')
        })
    except TokenError as e:
        return Response({
            'valid': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return Response({
            'valid': False,
            'error': f"Unexpected error: {str(e)}"
        }, status=400)
