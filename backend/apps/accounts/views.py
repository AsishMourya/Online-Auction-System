from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, viewsets

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Address, PaymentMethod, User
from .permissions import (
    seller_required,
)
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    PaymentMethodSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Create a new user account with email, password, and profile information.",
        responses={201: UserProfileSerializer, 400: "Bad Request"},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            with transaction.atomic():
                user = serializer.save()

                tokens = get_tokens_for_user(user)
                profile_serializer = UserProfileSerializer(user)

                role_msg = "buyer" if user.role == User.BUYER else "seller"

                return Response(
                    {
                        "message": f"User registered successfully as a {role_msg}.",
                        "tokens": tokens,
                        "user": profile_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        return Response(
            {"message": "Registration failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Login user",
        operation_description="Authenticate user with email and password.",
        responses={
            200: openapi.Response("Login Successful", UserProfileSerializer),
            400: "Bad Request",
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            tokens = get_tokens_for_user(user)
            return Response(
                {
                    "message": "Login successful.",
                    "tokens": tokens,
                    "user": UserProfileSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get user profile",
        operation_description="Retrieve logged in user's profile information.",
        responses={200: UserProfileSerializer},
    )
    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Update logged in user's profile information.",
        responses={200: UserProfileSerializer, 400: "Bad Request"},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if "role" in request.data and request.user.role != User.ADMIN:
            return Response(
                {"message": "You don't have permission to change role."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if "phone_number" in request.data:
            phone = request.data["phone_number"]
            if phone:
                digits_only = "".join(filter(str.isdigit, phone))
                if len(digits_only) != 10:
                    return Response(
                        {"message": "Phone number must contain exactly 10 digits."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                request.data["phone_number"] = digits_only

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Profile updated successfully.", "user": serializer.data}
            )
        return Response(
            {"message": "Profile update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="List user addresses",
        operation_description="Get all addresses for the logged in user.",
        responses={200: AddressSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "Addresses retrieved successfully.",
                "addresses": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Add address",
        operation_description="Add a new address for the logged in user.",
        responses={201: AddressSerializer, 400: "Bad Request"},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Address added successfully.", "address": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_summary="Get address details",
        operation_description="Get details of a specific address.",
        responses={200: AddressSerializer, 404: "Not Found"},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "Address details retrieved.", "address": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Update address",
        operation_description="Update an existing address.",
        responses={200: AddressSerializer, 400: "Bad Request", 404: "Not Found"},
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Address updated successfully.", "address": serializer.data}
            )
        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_summary="Delete address",
        operation_description="Delete an existing address.",
        responses={204: "No Content", 404: "Not Found"},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Address deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @swagger_auto_schema(
        operation_summary="Set default address",
        operation_description="Set an address as the default shipping address.",
        responses={200: AddressSerializer, 404: "Not Found"},
    )
    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(
            {
                "message": "Default address updated successfully.",
                "address": AddressSerializer(address).data,
            }
        )


class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="List payment methods",
        operation_description="Get all payment methods for the logged in user.",
        responses={200: PaymentMethodSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "Payment methods retrieved successfully.",
                "payment_methods": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Add payment method",
        operation_description="Add a new payment method for the logged in user.",
        responses={201: PaymentMethodSerializer, 400: "Bad Request"},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Payment method added successfully.",
                    "payment_method": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_summary="Get payment method details",
        operation_description="Get details of a specific payment method.",
        responses={200: PaymentMethodSerializer, 404: "Not Found"},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Payment method details retrieved.",
                "payment_method": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Delete payment method",
        operation_description="Delete an existing payment method.",
        responses={204: "No Content", 404: "Not Found"},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Payment method deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @swagger_auto_schema(
        operation_summary="Set default payment method",
        operation_description="Set a payment method as default.",
        responses={200: PaymentMethodSerializer, 404: "Not Found"},
    )
    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()
        return Response(
            {
                "message": "Default payment method updated successfully.",
                "payment_method": PaymentMethodSerializer(payment_method).data,
            }
        )


class ChangePasswordView(generics.GenericAPIView):
    """
    Endpoint for changing password
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change password",
        operation_description="Change the password for the logged-in user.",
        responses={
            200: "Password changed successfully",
            400: "Bad Request",
            401: "Unauthorized",
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = request.user

            if not user.check_password(
                serializer.validated_data.get("current_password")
            ):
                return Response(
                    {"message": "Current password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(serializer.validated_data.get("new_password"))
            user.save()

            update_session_auth_hash(request, user)

            return Response(
                {"message": "Password changed successfully."}, status=status.HTTP_200_OK
            )

        return Response(
            {"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(generics.GenericAPIView):
    """
    Logout endpoint to blacklist the user's refresh token
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Logout user",
        operation_description="Blacklist the current user's refresh token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={200: "Logout successful", 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"message": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)

            if str(token["user_id"]) != str(request.user.id):
                return Response(
                    {"message": "Token does not match current user."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            token.blacklist()

            return Response(
                {"message": "Logout successful."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"message": f"Logout failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_default_address(request):
    """
    Get the user's default address
    """
    try:
        address = Address.objects.get(user=request.user, is_default=True)
        return Response(
            {
                "message": "Default address retrieved successfully.",
                "address": AddressSerializer(address).data,
            }
        )
    except Address.DoesNotExist:
        return Response(
            {"message": "No default address found."}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_default_payment_method(request):
    """
    Get the user's default payment method
    """
    try:
        payment_method = PaymentMethod.objects.get(user=request.user, is_default=True)
        return Response(
            {
                "message": "Default payment method retrieved successfully.",
                "payment_method": PaymentMethodSerializer(payment_method).data,
            }
        )
    except PaymentMethod.DoesNotExist:
        return Response(
            {"message": "No default payment method found."},
            status=status.HTTP_404_NOT_FOUND,
        )
