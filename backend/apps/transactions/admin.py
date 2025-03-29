from django.contrib import admin
from .models import Transaction, TransactionLog, AutoBid


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
    list_display = ('id', 'user', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__email', 'user__username', 'description', 'reference')
    readonly_fields = (
        'id', 'user', 'transaction_type', 'amount', 
        'created_at', 'updated_at', 'completed_at'
    )
    inlines = [TransactionLogInline]
    fieldsets = (
        (None, {"fields": ("id", "user", "transaction_type", "amount", "status")}),
        ("Reference Information", {"fields": ("reference", "reference_id")}),
        ("Payment Details", {"fields": ("payment_method",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "completed_at")}),
    )


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('id', 'transaction', 'action', 'timestamp', 'status_before', 'status_after', 'details')


@admin.register(AutoBid)
class AutoBidAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'auction', 'max_amount', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__email', 'user__username', 'auction__title')
