from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import re


def validate_phone_number(value):
    if value:
        digits_only = "".join(filter(str.isdigit, str(value)))
        if len(digits_only) != 10:
            raise ValidationError(_("Phone number must contain exactly 10 digits."))


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValueError(_("Enter a valid email address"))

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ADMIN = "admin"
    STAFF = "staff"
    BIDDER = "bidder"
    BUYER = "buyer"
    SELLER = "seller"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (STAFF, "Staff"),
        (BIDDER, "Bidder"),
        (BUYER, "Buyer"),
        (SELLER, "Seller"),
    ]

    username = None
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        null=True,
        validators=[validate_phone_number],
    )
    role = models.CharField(
        _("role"), max_length=10, choices=ROLE_CHOICES, default=BUYER
    )
    is_active = models.BooleanField(_("active status"), default=True)
    signup_datetime = models.DateTimeField(_("signup date"), auto_now_add=True)
    last_login_datetime = models.DateTimeField(_("last login"), null=True, blank=True)

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def clean(self):
        """Validate model fields."""
        super().clean()

        if self.phone_number:
            validate_phone_number(self.phone_number)

        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        self.clean()

        if self.pk is not None:
            self.last_login_datetime = timezone.now()
        super().save(*args, **kwargs)


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_line1 = models.CharField(_("address line 1"), max_length=255)
    address_line2 = models.CharField(
        _("address line 2"), max_length=255, blank=True, null=True
    )
    city = models.CharField(_("city"), max_length=100)
    state = models.CharField(_("state/province"), max_length=100)
    postal_code = models.CharField(_("postal code"), max_length=20)
    country = models.CharField(_("country"), max_length=100)
    is_default = models.BooleanField(_("default address"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(
                is_default=False
            )
        elif not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_default = True
        elif (
            not self.is_default
            and not Address.objects.filter(user=self.user, is_default=True)
            .exclude(pk=self.pk)
            .exists()
        ):
            self.is_default = True

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_default:
            other_address = (
                Address.objects.filter(user=self.user).exclude(pk=self.pk).first()
            )
            if other_address:
                other_address.is_default = True
                other_address.save()
        super().delete(*args, **kwargs)


class PaymentMethod(models.Model):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CRYPTO = "crypto"
    BANK = "bank"

    PAYMENT_TYPE_CHOICES = [
        (CREDIT_CARD, "Credit Card"),
        (DEBIT_CARD, "Debit Card"),
        (CRYPTO, "Cryptocurrency"),
        (BANK, "Bank Transfer"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_methods"
    )
    payment_type = models.CharField(
        _("payment type"), max_length=20, choices=PAYMENT_TYPE_CHOICES
    )
    provider = models.CharField(_("provider name"), max_length=100)
    account_identifier = models.CharField(_("account identifier"), max_length=100)
    is_default = models.BooleanField(_("default payment method"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.provider}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Unset any other default payment method for this user
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(
                is_default=False
            )
        elif not self.pk and not PaymentMethod.objects.filter(user=self.user).exists():
            # First payment method for this user, set as default
            self.is_default = True
        elif (
            not self.is_default
            and not PaymentMethod.objects.filter(user=self.user, is_default=True)
            .exclude(pk=self.pk)
            .exists()
        ):
            # No other default payment method exists, make this one default
            self.is_default = True

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # If this is the default payment method, set another payment method as default before deleting
        if self.is_default:
            # Find another payment method to make default
            other_payment_method = (
                PaymentMethod.objects.filter(user=self.user).exclude(pk=self.pk).first()
            )
            if other_payment_method:
                other_payment_method.is_default = True
                other_payment_method.save()
        super().delete(*args, **kwargs)
