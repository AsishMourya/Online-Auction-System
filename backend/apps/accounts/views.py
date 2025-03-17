from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, viewsets

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Address, PaymentMethod
from .permissions import IsOwner
from .serializers import (
    AddressSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
    UserProfileBasicSerializer,
    UserRegistrationSerializer,
)

from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserPasswordChangeSerializer,
)

from apps.core.mixins import SwaggerSchemaMixin


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_summary="Obtain JWT tokens",
        operation_description="Get access and refresh tokens by providing email and password",
        responses={200: CustomTokenObtainPairSerializer},
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200 and request.data.get("email"):
            user = User.objects.filter(email=request.data.get("email")).first()
            if user:
                user.last_login_datetime = timezone.now()
                user.save(update_fields=["last_login_datetime"])

        return response


class UserRegistrationView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
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
            user = serializer.save()

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "message": "User registered successfully",
                    "user": UserProfileBasicSerializer(user).data,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ModelViewSet):
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
        return Response(serializer.data)

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
        return Response(serializer.data)

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
                return Response(
                    {"old_password": "Incorrect password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(new_password)
            user.save()

            return Response({"message": "Password changed successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
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
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
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
        return Response(serializer.data)


class PaymentMethodViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
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
        operation_description="Add a new payment method for current user",
        responses={201: PaymentMethodSerializer},
        tags=["Payment Methods"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data["user"] = request.user

        is_default = serializer.validated_data.get("is_default", False)

        if not PaymentMethod.objects.filter(user=request.user).exists():
            serializer.validated_data["is_default"] = True
        elif is_default:
            PaymentMethod.objects.filter(user=request.user, is_default=True).update(
                is_default=False
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @swagger_auto_schema(
        operation_summary="Set default payment method",
        operation_description="Set a payment method as default",
        responses={200: PaymentMethodSerializer},
        tags=["Payment Methods"],
    )
    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        payment_method = self.get_object()

        PaymentMethod.objects.filter(user=request.user, is_default=True).update(
            is_default=False
        )

        payment_method.is_default = True
        payment_method.save()

        serializer = self.get_serializer(payment_method)
        return Response(serializer.data)


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
        return Response(
            {"message": "Logged out successfully"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
