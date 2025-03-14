from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Address, PaymentMethod


class AddressInline(admin.TabularInline):
    """Inline view for addresses"""

    model = Address
    extra = 0
    fields = (
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "country",
        "is_default",
    )


class PaymentMethodInline(admin.TabularInline):
    """Inline view for payment methods"""

    model = PaymentMethod
    extra = 0
    fields = ("payment_type", "provider", "account_identifier", "is_default")
    readonly_fields = ("provider", "account_identifier")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""

    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "signup_datetime",
        "last_login_datetime",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("-signup_datetime",)
    readonly_fields = ("signup_datetime", "last_login_datetime")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("signup_datetime", "last_login_datetime")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "role",
                    "is_active",
                ),
            },
        ),
    )

    inlines = [AddressInline, PaymentMethodInline]

    def save_model(self, request, obj, form, change):
        """Override save method to handle password hashing"""
        if not change:
            obj.set_password(form.cleaned_data["password"])
        super().save_model(request, obj, form, change)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for addresses"""

    list_display = ("address_line1", "city", "state", "country", "user", "is_default")
    list_filter = ("is_default", "country", "state", "city")
    search_fields = (
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "country",
        "user__email",
    )
    raw_id_fields = ("user",)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for payment methods"""

    list_display = (
        "payment_type",
        "provider",
        "account_identifier",
        "user",
        "is_default",
    )
    list_filter = ("payment_type", "is_default", "provider")
    search_fields = ("provider", "account_identifier", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("provider", "account_identifier")
