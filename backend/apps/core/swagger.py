from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


swagger_tags = [
    {
        "name": "Authentication",
        "description": "API endpoints for user authentication and registration",
    },
    {"name": "Users", "description": "User profile management"},
    {"name": "Addresses", "description": "User shipping and billing addresses"},
    {"name": "Payment Methods", "description": "User payment methods"},
    {"name": "Categories", "description": "Item categories"},
    {"name": "Items", "description": "User items management"},
    {"name": "Auctions", "description": "Auction listings and management"},
    {"name": "Bids", "description": "Bidding on auctions"},
    {"name": "AutoBids", "description": "Automatic bidding configuration"},
    {"name": "Transactions", "description": "Financial transactions"},
    {"name": "Wallet", "description": "User wallet management"},
    {"name": "Notifications", "description": "User notifications"},
    {
        "name": "Notification Preferences",
        "description": "User notification preferences",
    },
]


def get_swagger_view(api_url_patterns):
    return get_schema_view(
        openapi.Info(
            title="Auction House API",
            default_version="v1",
            description="API for the Auction House platform",
            terms_of_service="https://www.auctionhouse.com/terms/",
            contact=openapi.Contact(email="support@auctionhouse.com"),
            license=openapi.License(name="Private License"),
        ),
        public=True,
        permission_classes=[permissions.AllowAny],
        authentication_classes=[],
        patterns=api_url_patterns,
    )
