from django.db.models import Count
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Address, PaymentMethod, User
from .permissions import IsAdmin, admin_required
from .serializers import (
    AddressSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
)


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage all users
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()

    @swagger_auto_schema(
        operation_summary="List all users (Admin)",
        operation_description="Admin can view all users in the system.",
        responses={200: UserProfileSerializer(many=True), 403: "Permission Denied"},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"message": "Users retrieved successfully.", "users": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Activate/Deactivate user (Admin)",
        operation_description="Admin can activate or deactivate a user account.",
        responses={
            200: UserProfileSerializer,
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
                "user": UserProfileSerializer(user).data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Change user role (Admin)",
        operation_description="Admin can change a user's role.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "role": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="User role",
                    enum=["admin", "staff", "bidder", "buyer", "seller"],
                )
            },
            required=["role"],
        ),
        responses={
            200: UserProfileSerializer,
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
                "user": UserProfileSerializer(user).data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Create admin user (Admin only)",
        operation_description="Admin can create other admin users.",
        request_body=UserProfileSerializer,
        responses={
            201: UserProfileSerializer,
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


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@admin_required
def admin_dashboard(request):
    """Admin dashboard view example"""
    user_count = User.objects.count()
    address_count = Address.objects.count()
    payment_method_count = PaymentMethod.objects.count()

    users_by_role = User.objects.values("role").annotate(count=Count("id"))
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()

    return Response(
        {
            "message": "Admin dashboard data retrieved successfully.",
            "stats": {
                "user_count": user_count,
                "address_count": address_count,
                "payment_method_count": payment_method_count,
                "users_by_role": list(users_by_role),
                "active_users": active_users,
                "inactive_users": inactive_users,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
def all_addresses(request):
    """Admin endpoint to get all addresses in the system"""
    addresses = Address.objects.all()
    serializer = AddressSerializer(addresses, many=True)
    return Response(
        {
            "message": "All addresses retrieved successfully.",
            "addresses": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
def user_addresses(request, user_id):
    """Admin endpoint to get addresses for a specific user"""
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
def all_payment_methods(request):
    """Admin endpoint to get all payment methods in the system"""
    payment_methods = PaymentMethod.objects.all()
    serializer = PaymentMethodSerializer(payment_methods, many=True)
    return Response(
        {
            "message": "All payment methods retrieved successfully.",
            "payment_methods": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
def user_payment_methods(request, user_id):
    """Admin endpoint to get payment methods for a specific user"""
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
