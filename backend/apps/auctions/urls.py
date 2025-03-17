from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    AuctionViewSet,
    BidViewSet,
    search_auctions,
    auction_stats,
    search_items,
    list_all_categories,
    AutoBidViewSet,
)

from .admin_views import (
    AdminAuctionViewSet,
    AdminBidViewSet,
    admin_auction_dashboard,
    admin_export_auctions,
    admin_export_bids,
    admin_verify_auction,
    admin_hide_auction,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"auctions", AuctionViewSet, basename="auction")
router.register(r"bids", BidViewSet, basename="bid")
router.register(r"autobids", AutoBidViewSet, basename="autobid")

admin_router = DefaultRouter()
admin_router.register(r"auctions", AdminAuctionViewSet, basename="admin-auction")
admin_router.register(r"bids", AdminBidViewSet, basename="admin-bid")

urlpatterns = [
    # Standard API endpoints
    path("", include(router.urls)),
    path("search/", search_auctions, name="search-auctions"),
    path("search/items/", search_items, name="search-items"),
    path("categories/all/", list_all_categories, name="list-all-categories"),
    path("auctions/<uuid:auction_id>/stats/", auction_stats, name="auction-stats"),
    # Admin API endpoints
    path("admin/", include(admin_router.urls)),
    path("admin/dashboard/", admin_auction_dashboard, name="admin-auction-dashboard"),
    path("admin/auctions/export/", admin_export_auctions, name="admin-export-auctions"),
    path("admin/bids/export/", admin_export_bids, name="admin-export-bids"),
    path(
        "admin/auctions/<uuid:auction_id>/verify/",
        admin_verify_auction,
        name="admin-verify-auction",
    ),
    path(
        "admin/auctions/<uuid:auction_id>/hide/",
        admin_hide_auction,
        name="admin-hide-auction",
    ),
]
