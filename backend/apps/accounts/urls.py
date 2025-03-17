from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AddressViewSet,
    CustomTokenObtainPairView,
    PaymentMethodViewSet,
    UserProfileViewSet,
    UserRegistrationView,
    logout_view,
)
from .admin_views import (
    AdminUserManagementViewSet,
    admin_dashboard,
    all_addresses,
    all_payment_methods,
    user_addresses,
    user_payment_methods,
)

# Setup router for standard API endpoints
router = DefaultRouter()
router.register(r"profile", UserProfileViewSet, basename="profile")
router.register(r"addresses", AddressViewSet, basename="address")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")

# Setup router for admin API endpoints
admin_router = DefaultRouter()
admin_router.register(r"users", AdminUserManagementViewSet, basename="admin-user")

urlpatterns = [
    # Auth endpoints
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),
    path("", include(router.urls)),
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
]
