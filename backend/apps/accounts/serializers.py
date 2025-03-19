from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, PaymentMethod, User, Wallet


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user info with tokens"""

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user data to response
        user = self.user
        data["user"] = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
        }

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_number",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords don't match."}
            )

        # Run Django's password validators
        validate_password(attrs["password"])

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileBasicSerializer(serializers.ModelSerializer):
    """Basic user profile serializer for nested relationships"""

    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name"]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class UserProfileSerializer(serializers.ModelSerializer):
    """Full user profile serializer"""

    addresses = serializers.SerializerMethodField()
    payment_methods = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "is_active",
            "addresses",
            "payment_methods",
            "signup_datetime",
            "last_login_datetime",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "is_active",
            "signup_datetime",
            "last_login_datetime",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_addresses(self, obj):
        addresses = Address.objects.filter(user=obj)
        return AddressSerializer(addresses, many=True).data

    def get_payment_methods(self, obj):
        payment_methods = PaymentMethod.objects.filter(user=obj)
        return PaymentMethodSerializer(payment_methods, many=True).data


class UserPasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change endpoint"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Password fields didn't match."}
            )

        # Run Django's password validators
        validate_password(attrs["new_password"])

        return attrs


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for user addresses"""

    class Meta:
        model = Address
        fields = [
            "id",
            "user",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for user payment methods"""

    payment_type_display = serializers.CharField(
        source="get_payment_type_display", read_only=True
    )

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "user",
            "payment_type",
            "payment_type_display",
            "provider",
            "account_identifier",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]
        extra_kwargs = {"account_identifier": {"write_only": False, "read_only": False}}


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    total_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="balance", read_only=True
    )
    active_bids_count = serializers.SerializerMethodField()
    won_auctions_count = serializers.SerializerMethodField()

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
            "active_bids_count",
            "won_auctions_count",
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
            "active_bids_count",
            "won_auctions_count",
            "created_at",
            "updated_at",
        ]
        ref_name = "AccountWalletSerializer"

    def get_active_bids_count(self, obj):
        """Get count of active bids for this user"""
        from apps.auctions.models import Bid

        return Bid.objects.filter(bidder=obj.user, status=Bid.STATUS_ACTIVE).count()

    def get_won_auctions_count(self, obj):
        """Get count of auctions won by this user"""
        from apps.auctions.models import Bid

        return Bid.objects.filter(bidder=obj.user, status=Bid.STATUS_WON).count()
