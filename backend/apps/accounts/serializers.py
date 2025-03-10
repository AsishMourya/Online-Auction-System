from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.crypto import get_random_string
import random
import re

from .models import User, Address, PaymentMethod


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
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
            "role",
        ]

    def validate_email(self, value):
        """Validate email format and that it isn't already in use."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Enter a valid email address.")

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")

        return value.lower()

    def validate_phone_number(self, value):
        """Validate that phone numbers contain exactly 10 digits."""
        if value:
            digits_only = re.sub(r"\D", "", value)
            if len(digits_only) != 10:
                raise serializers.ValidationError(
                    "Phone number must contain exactly 10 digits."
                )
            return digits_only
        return value

    def validate_role(self, value):
        """Validate that public registrations can only be buyer or seller."""
        request = self.context.get("request")

        if (
            not request
            or not request.user.is_authenticated
            or request.user.role != User.ADMIN
        ):
            if value not in [User.BUYER, User.SELLER]:
                raise serializers.ValidationError(
                    "Public registration is only available for buyer or seller roles."
                )

        return value

    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )

        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one number."
            )
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one letter."
            )

        return value

    def validate(self, data):
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError({"message": "Passwords do not match."})

        if len(data.get("first_name", "")) < 1 or len(data.get("last_name", "")) < 1:
            raise serializers.ValidationError(
                {"message": "First and last name are required."}
            )

        if data.get("role") == User.ADMIN:
            request = self.context.get("request")

            if (
                not request
                or not request.user.is_authenticated
                or request.user.role != User.ADMIN
            ):
                raise serializers.ValidationError(
                    {"role": "Only existing admins can create admin users."}
                )

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, data):
        user = authenticate(email=data.get("email"), password=data.get("password"))
        if not user:
            raise serializers.ValidationError(
                {"message": "Invalid credentials. Please try again."}
            )
        if not user.is_active:
            raise serializers.ValidationError({"message": "User account is disabled."})

        user.save()
        data["user"] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "is_active",
            "signup_datetime",
            "last_login_datetime",
        ]
        read_only_fields = ["email", "signup_datetime", "last_login_datetime"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "payment_type", "provider", "account_identifier", "is_default"]
        read_only_fields = ["provider", "account_identifier"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user

        payment_type = validated_data.get("payment_type")
        if (
            payment_type == PaymentMethod.CREDIT_CARD
            or payment_type == PaymentMethod.DEBIT_CARD
        ):
            card_providers = ["Visa", "MasterCard", "American Express", "Discover"]
            validated_data["provider"] = random.choice(card_providers)
            validated_data["account_identifier"] = (
                f"**** **** **** {random.randint(1000, 9999)}"
            )

        elif payment_type == PaymentMethod.CRYPTO:
            crypto_providers = ["Bitcoin", "Ethereum", "Litecoin", "Ripple"]
            validated_data["provider"] = random.choice(crypto_providers)
            validated_data["account_identifier"] = (
                f"0x{get_random_string(40, '0123456789abcdef')}"
            )

        elif payment_type == PaymentMethod.BANK:
            bank_providers = ["Chase", "Bank of America", "Wells Fargo", "Citibank"]
            validated_data["provider"] = random.choice(bank_providers)
            validated_data["account_identifier"] = f"****{random.randint(1000, 9999)}"

        return super().create(validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint"""

    current_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    confirm_new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, data):
        if data.get("new_password") != data.get("confirm_new_password"):
            raise serializers.ValidationError({"message": "New passwords don't match."})

        new_password = data.get("new_password")
        if len(new_password) < 8:
            raise serializers.ValidationError(
                {"message": "Password must be at least 8 characters long."}
            )

        if not any(char.isdigit() for char in new_password):
            raise serializers.ValidationError(
                {"message": "Password must contain at least one number."}
            )

        if not any(char.isalpha() for char in new_password):
            raise serializers.ValidationError(
                {"message": "Password must contain at least one letter."}
            )

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset"""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a password reset"""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, data):
        if data.get("new_password") != data.get("confirm_password"):
            raise serializers.ValidationError({"message": "Passwords don't match."})
        return data
