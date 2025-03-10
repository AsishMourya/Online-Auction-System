from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    AddressViewSet,
    PaymentMethodViewSet,
    ChangePasswordView,
    LogoutView,
    get_default_address,
    get_default_payment_method,
)

from .admin_views import (
    AdminUserManagementViewSet,
    admin_dashboard,
    all_addresses,
    user_addresses,
    all_payment_methods,
    user_payment_methods,
)

router = DefaultRouter()
router.register(r"addresses", AddressViewSet, basename="address")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")

admin_router = DefaultRouter()
admin_router.register(
    r"users", AdminUserManagementViewSet, basename="admin-user-management"
)

urlpatterns = [
    # Auth endpoints
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("login/", UserLoginView.as_view(), name="user-login"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # User endpoints
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("default-address/", get_default_address, name="default-address"),
    path(
        "default-payment-method/",
        get_default_payment_method,
        name="default-payment-method",
    ),
    # Admin endpoints
    path("admin/", include(admin_router.urls)),
    path("admin/dashboard/", admin_dashboard, name="admin-dashboard"),
    path("admin/addresses/", all_addresses, name="admin-all-addresses"),
    path(
        "admin/addresses/user/<int:user_id>/",
        user_addresses,
        name="admin-user-addresses",
    ),
    path(
        "admin/payment-methods/", all_payment_methods, name="admin-all-payment-methods"
    ),
    path(
        "admin/payment-methods/user/<int:user_id>/",
        user_payment_methods,
        name="admin-user-payment-methods",
    ),
    # Include default router
    path("", include(router.urls)),
]
