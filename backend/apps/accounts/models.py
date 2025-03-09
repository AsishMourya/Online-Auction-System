from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if username is None:
            raise ValueError("Users must have a username.")
        if email is None:
            raise ValueError("Users must have an email address.")
        if password is None:
            raise ValueError("Users must have a password.")
        user = self.model(
            username=username, email=self.normalize_email(email), **extra_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        if password is None:
            raise ValueError("Users must have a password.")
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        user = self.create_user(username, email, password, **extra_fields)
        user.save()
        return user


class UserRoles(models.Model):
    ADMIN = "admin"
    SELLER = "seller"
    BUYER = "buyer"
    STAFF = "staff"

    USER_ROLES = [
        (ADMIN, "Admin"),
        (SELLER, "Seller"),
        (BUYER, "Buyer"),
        (STAFF, "Staff"),
    ]

    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, choices=USER_ROLES, default=BUYER)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _str_(self):
        return self.role_name

    class Meta:
        db_table = "user_roles"


# User Model
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=True)
    role = models.ForeignKey(
        UserRoles, on_delete=models.CASCADE, default=UserRoles.BUYER
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "first_name", "password"]

    def _str_(self):
        return self.username

    class Meta:
        db_table = "users"


class ShippingAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line_1 = models.TextField(max_length=255)
    address_line_2 = models.TextField(max_length=255, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shipping_addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address",
            )
        ]

    def _str_(self):
        return f"{self.address_line_1}, {self.city}, {self.state}, {self.zip_code}, {self.country} for {self.user.username}"

    def save(self, *args, **kwargs):
        if self.is_default:
            try:
                temp = ShippingAddress.objects.get(user=self.user, is_default=True)
                if self != temp:
                    temp.is_default = False
                    temp.save()
            except ShippingAddress.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    class PaymentType(models.TextChoices):
        CREDIT_CARD = "credit_card"
        DEBIT_CARD = "debit_card"
        PAYPAL = "paypal"
        BANKTRANSFER = "bank_transfer"
        CRYPTOCURRENCY = "cryptocurrency"

    payment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=50, choices=PaymentType.choices)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_methods"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_payment",
            )
        ]

    def _str_(self):
        return f"{self.payment_type} for {self.user.username}"

    def save(self, *args, **kwargs):
        if self.is_default:
            try:
                temp = PaymentMethod.objects.get(user=self.user, is_default=True)
                if self != temp:
                    temp.is_default = False
                    temp.save()
            except PaymentMethod.DoesNotExist:
                pass
        super().save(*args, **kwargs)