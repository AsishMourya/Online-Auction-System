from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TransactionViewSet, get_account_balance, WalletViewSet
from .admin_views import (
    AdminTransactionViewSet,
    admin_transaction_stats,
    admin_process_refund,
)

router = DefaultRouter()
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"wallet", WalletViewSet, basename="wallet")

admin_router = DefaultRouter()
admin_router.register(
    r"transactions", AdminTransactionViewSet, basename="admin-transaction"
)

urlpatterns = [
    # Standard API endpoints
    path("", include(router.urls)),
    path("account/balance/", get_account_balance, name="account-balance"),
    # Admin API endpoints
    path("admin/", include(admin_router.urls)),
    path("admin/stats/", admin_transaction_stats, name="admin-transaction-stats"),
    path("admin/process-refund/", admin_process_refund, name="admin-process-refund"),
]
