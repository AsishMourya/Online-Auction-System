from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Address, PaymentMethod, Wallet


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


class WalletInline(admin.TabularInline):
    """Inline view for user wallet"""

    model = Wallet
    extra = 0
    fields = ("balance", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


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
    )
    list_filter = ("role", "is_active", "signup_datetime")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-signup_datetime",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number")}),
        (
            _("Permissions"),
            {"fields": ("role", "is_active", "is_staff", "is_superuser")},
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
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "role",
                ),
            },
        ),
    )

    inlines = [WalletInline, AddressInline, PaymentMethodInline]
    readonly_fields = ("signup_datetime", "last_login_datetime")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "address_line1", "city", "country", "is_default")
    list_filter = ("is_default", "country", "city")
    search_fields = ("user__email", "address_line1", "city", "country")
    raw_id_fields = ("user",)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "payment_type", "provider", "is_default")
    list_filter = ("payment_type", "is_default")
    search_fields = ("user__email", "provider")
    raw_id_fields = ("user",)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")

    actions = ["add_funds"]

    def add_funds(self, request, queryset):
        """Admin action to add funds to selected wallets"""
        for wallet in queryset:
            wallet.balance += 1000
            wallet.save()

        self.message_user(request, f"Added 1000 to {queryset.count()} wallet(s)")

    add_funds.short_description = "Add 1000 to selected wallets"
