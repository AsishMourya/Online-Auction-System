from django.contrib import admin
from .models import Transaction, AccountBalance, TransactionLog


class TransactionLogInline(admin.TabularInline):
    model = TransactionLog
    extra = 0
    readonly_fields = (
        "timestamp",
        "action",
        "status_before",
        "status_after",
        "details",
    )
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "transaction_type",
        "amount",
        "status",
        "created_at",
        "completed_at",
    )
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("user__email", "reference", "reference_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TransactionLogInline]
    fieldsets = (
        (None, {"fields": ("id", "user", "transaction_type", "amount", "status")}),
        ("Reference Information", {"fields": ("reference", "reference_id")}),
        ("Payment Details", {"fields": ("payment_method", "external_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "completed_at")}),
    )


@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "available_balance",
        "pending_balance",
        "held_balance",
        "total_balance",
        "last_updated",
    )
    search_fields = ("user__email",)
    readonly_fields = ("last_updated", "total_balance")

    def total_balance(self, obj):
        return obj.total_balance


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "action", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("transaction__reference", "action")
    readonly_fields = ("timestamp",)
