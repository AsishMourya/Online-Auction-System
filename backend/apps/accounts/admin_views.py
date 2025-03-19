from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Address, PaymentMethod, User, Wallet
from .permissions import IsAdmin, admin_required
from .serializers import (
    AddressSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
    UserProfileBasicSerializer,
    WalletSerializer,
)


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage all users
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    lookup_field = "pk"

    @swagger_auto_schema(
        operation_id="admin_list_users",
        operation_summary="List all users (Admin)",
        operation_description="Admin can view all users in the system.",
        tags=["Admin - User Management"],
        responses={
            200: UserProfileBasicSerializer(many=True),
            403: "Permission Denied",
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserProfileBasicSerializer(queryset, many=True)
        return Response(
            {"message": "Users retrieved successfully.", "users": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_get_user_detail",
        operation_summary="Get user details (Admin)",
        operation_description="Admin can view detailed user information including addresses and payment methods.",
        tags=["Admin - User Management"],
        responses={
            200: UserProfileSerializer,
            403: "Permission Denied",
            404: "User not found",
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "User details retrieved successfully.", "user": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_toggle_user_status",
        operation_summary="Activate/Deactivate user (Admin)",
        operation_description="Admin can activate or deactivate a user account.",
        tags=["Admin - User Management"],
        responses={
            200: UserProfileBasicSerializer,
            403: "Permission Denied",
            404: "Not Found",
        },
    )
    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        status_text = "activated" if user.is_active else "deactivated"
        return Response(
            {
                "message": f"User {status_text} successfully.",
                "user": UserProfileBasicSerializer(user).data,
            }
        )

    @swagger_auto_schema(
        operation_id="admin_change_user_role",
        operation_summary="Change user role (Admin)",
        operation_description="Admin can change a user's role.",
        tags=["Admin - User Management"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "role": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="User role",
                    enum=["admin", "staff", "user"],
                )
            },
            required=["role"],
        ),
        responses={
            200: UserProfileBasicSerializer,
            400: "Bad Request",
            403: "Permission Denied",
        },
    )
    @action(detail=True, methods=["post"])
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get("role")

        if not new_role or new_role not in [role[0] for role in User.ROLE_CHOICES]:
            return Response(
                {
                    "message": "Invalid role specified. Valid roles are: "
                    + ", ".join([role[0] for role in User.ROLE_CHOICES])
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            user.id == request.user.id
            and user.role == User.ADMIN
            and new_role != User.ADMIN
        ):
            return Response(
                {"message": "Cannot change your own admin role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = new_role
        user.save()

        return Response(
            {
                "message": f"User role changed to {new_role} successfully.",
                "user": UserProfileBasicSerializer(user).data,
            }
        )

    @swagger_auto_schema(
        operation_id="admin_create_user",
        operation_summary="Create user (Admin only)",
        operation_description="Admin can create users with any role.",
        tags=["Admin - User Management"],
        request_body=UserProfileSerializer,
        responses={
            201: UserProfileBasicSerializer,
            400: "Bad Request",
            403: "Permission Denied",
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Admin user created successfully.",
                    "user": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"])
    def wallet(self, request, pk=None):
        """Get wallet details for a user"""
        user = self.get_object()
        wallet, created = Wallet.objects.get_or_create(user=user)
        serializer = WalletSerializer(wallet)
        return Response(
            {"wallet": serializer.data, "message": "Wallet retrieved successfully"}
        )

    @action(detail=True, methods=["post"])
    def add_funds(self, request, pk=None):
        """Add funds to a user's wallet (admin only)"""
        user = self.get_object()
        amount = request.data.get("amount")

        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {"detail": "Amount must be greater than zero"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        wallet, created = Wallet.objects.get_or_create(user=user)
        wallet.deposit(amount)

        # Create a record in the system
        from apps.transactions.models import Transaction
        from django.utils import timezone

        Transaction.objects.create(
            user=user,
            transaction_type="deposit",
            amount=amount,
            status="completed",
            reference="Admin deposit",
            completed_at=timezone.now(),
        )

        serializer = WalletSerializer(wallet)
        return Response(
            {
                "wallet": serializer.data,
                "message": f"Added ${amount} to wallet successfully",
            }
        )

    @action(detail=True, methods=["get"])
    def auction_stats(self, request, pk=None):
        """Get auction statistics for a user"""
        user = self.get_object()

        from apps.auctions.models import Auction, Bid

        auctions_created = Auction.objects.filter(seller=user).count()
        active_auctions = Auction.objects.filter(seller=user, status="active").count()
        sold_auctions = Auction.objects.filter(seller=user, status="sold").count()

        bids_placed = Bid.objects.filter(bidder=user).count()
        auctions_won = Bid.objects.filter(bidder=user, status="won").count()

        total_spent = (
            Bid.objects.filter(bidder=user, status="won").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        total_earned = (
            Auction.objects.filter(seller=user, status="sold").aggregate(
                total=Sum("bids__amount", filter=Q(bids__status="won"))
            )["total"]
            or 0
        )

        return Response(
            {
                "user_id": str(user.id),
                "email": user.email,
                "auctions_stats": {
                    "created": auctions_created,
                    "active": active_auctions,
                    "sold": sold_auctions,
                },
                "bidding_stats": {
                    "bids_placed": bids_placed,
                    "auctions_won": auctions_won,
                    "total_spent": total_spent,
                    "total_earned": total_earned,
                },
            }
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@admin_required
@swagger_auto_schema(
    operation_id="admin_dashboard",
    operation_summary="Admin Dashboard",
    operation_description="Admin dashboard with user statistics",
    tags=["Admin - Dashboard"],
    responses={200: "Dashboard data", 403: "Permission Denied"},
)
def admin_dashboard(request):
    """Admin dashboard view example"""
    user_count = User.objects.count()
    address_count = Address.objects.count()
    payment_method_count = PaymentMethod.objects.count()

    users_by_role = User.objects.values("role").annotate(count=Count("id"))
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()

    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)

    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_month = User.objects.filter(signup_datetime__gte=thirty_days_ago).count()

    # Wallet statistics
    total_wallet_balance = Wallet.objects.aggregate(total=Sum("balance"))["total"] or 0
    avg_wallet_balance = Wallet.objects.aggregate(avg=Avg("balance"))["avg"] or 0

    # Transaction statistics
    from apps.transactions.models import Transaction

    total_deposits = (
        Transaction.objects.filter(transaction_type="deposit").aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    total_withdrawals = (
        Transaction.objects.filter(transaction_type="withdrawal").aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # Recent users
    recent_users = User.objects.order_by("-signup_datetime")[:5]
    recent_user_data = []

    for user in recent_users:
        wallet = Wallet.objects.filter(user=user).first()
        balance = wallet.balance if wallet else 0

        recent_user_data.append(
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": f"{user.first_name} {user.last_name}",
                "signup_date": user.signup_datetime,
                "wallet_balance": balance,
            }
        )

    return Response(
        {
            "user_stats": {
                "total": total_users,
                "active": active_users,
                "new_this_month": new_users_month,
            },
            "wallet_stats": {
                "total_balance": total_wallet_balance,
                "average_balance": avg_wallet_balance,
                "total_deposits": total_deposits,
                "total_withdrawals": total_withdrawals,
            },
            "recent_users": recent_user_data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
@swagger_auto_schema(
    operation_id="admin_list_all_addresses",
    operation_summary="List All Addresses (Admin)",
    operation_description="Admin endpoint to get all addresses in the system",
    tags=["Admin - Addresses"],
    responses={200: AddressSerializer(many=True), 403: "Permission Denied"},
)
def all_addresses(request):
    addresses = Address.objects.all()

    # Allow filtering
    user_id = request.query_params.get("user_id")
    if user_id:
        addresses = addresses.filter(user_id=user_id)

    country = request.query_params.get("country")
    if country:
        addresses = addresses.filter(country__iexact=country)

    serializer = AddressSerializer(addresses, many=True)
    return Response(
        {
            "message": "All addresses retrieved successfully.",
            "addresses": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
@swagger_auto_schema(
    operation_id="admin_list_user_addresses",
    operation_summary="List User Addresses (Admin)",
    operation_description="Admin endpoint to get addresses for a specific user",
    tags=["Admin - Addresses"],
    responses={
        200: AddressSerializer(many=True),
        403: "Permission Denied",
        404: "User not found",
    },
)
def user_addresses(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        addresses = Address.objects.filter(user=user)
        serializer = AddressSerializer(addresses, many=True)
        return Response(
            {
                "message": f"Addresses for user {user.email} retrieved successfully.",
                "addresses": serializer.data,
            }
        )
    except User.DoesNotExist:
        return Response(
            {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsAdmin])
@swagger_auto_schema(
    operation_id="admin_list_all_payment_methods",
    operation_summary="List All Payment Methods (Admin)",
    operation_description="Admin endpoint to get all payment methods in the system",
    tags=["Admin - Payment Methods"],
    responses={200: PaymentMethodSerializer(many=True), 403: "Permission Denied"},
)
def all_payment_methods(request):
    payment_methods = PaymentMethod.objects.all()

    # Allow filtering
    user_id = request.query_params.get("user_id")
    if user_id:
        payment_methods = payment_methods.filter(user_id=user_id)

    payment_type = request.query_params.get("payment_type")
    if payment_type:
        payment_methods = payment_methods.filter(payment_type=payment_type)

    serializer = PaymentMethodSerializer(payment_methods, many=True)
    return Response(
        {
            "message": "All payment methods retrieved successfully.",
            "payment_methods": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
@swagger_auto_schema(
    operation_id="admin_list_user_payment_methods",
    operation_summary="List User Payment Methods (Admin)",
    operation_description="Admin endpoint to get payment methods for a specific user",
    tags=["Admin - Payment Methods"],
    responses={
        200: PaymentMethodSerializer(many=True),
        403: "Permission Denied",
        404: "User not found",
    },
)
def user_payment_methods(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        payment_methods = PaymentMethod.objects.filter(user=user)
        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response(
            {
                "message": f"Payment methods for user {user.email} retrieved successfully.",
                "payment_methods": serializer.data,
            }
        )
    except User.DoesNotExist:
        return Response(
            {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
        )
