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

# Setup nested routers for better resource organization
router = DefaultRouter()
router.register(r"users/me/addresses", AddressViewSet, basename="user-address")
router.register(
    r"users/me/payment-methods", PaymentMethodViewSet, basename="user-payment-method"
)

# Admin router
admin_router = DefaultRouter()
admin_router.register(
    r"users", AdminUserManagementViewSet, basename="admin-user-management"
)

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", UserRegistrationView.as_view(), name="user-register"),
    path("auth/login/", UserLoginView.as_view(), name="user-login"),
    path("auth/logout/", LogoutView.as_view(), name="user-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # User profile endpoints
    path("users/me/", UserProfileView.as_view(), name="user-profile"),
    path(
        "users/me/change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("users/me/default-address/", get_default_address, name="default-address"),
    path(
        "users/me/default-payment-method/",
        get_default_payment_method,
        name="default-payment-method",
    ),
    # Admin endpoints
    path("admin/", include(admin_router.urls)),
    path("admin/dashboard/", admin_dashboard, name="admin-dashboard"),
    path("admin/addresses/", all_addresses, name="admin-all-addresses"),
    path(
        "admin/users/<uuid:user_id>/addresses/",
        user_addresses,
        name="admin-user-addresses",
    ),
    path(
        "admin/payment-methods/", all_payment_methods, name="admin-all-payment-methods"
    ),
    path(
        "admin/users/<uuid:user_id>/payment-methods/",
        user_payment_methods,
        name="admin-user-payment-methods",
    ),
    # Include default router for all other endpoints
    path("", include(router.urls)),
]
