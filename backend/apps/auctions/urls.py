from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    AuctionViewSet,
    BidViewSet,
    AutoBidViewSet,
    search_auctions,
    auction_stats,
    search_items,
    list_all_categories,
    test_auth,
    create_auction  # Your actual function-based view
)
from . import api  # Import the api module with the place_bid function

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'auctions', AuctionViewSet, basename='auction')
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'autobids', AutoBidViewSet, basename='autobid')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', search_auctions, name='search-auctions'),
    path('auctions/<uuid:auction_id>/stats/', auction_stats, name='auction-stats'),
    path('items/search/', search_items, name='search-items'),
    path('categories/all/', list_all_categories, name='list-all-categories'),
    path('test-auth/', test_auth, name='test-auth'),
    # Use your function-based view for auction creation
    path('create-auction/', create_auction, name='create-auction'),

    # Add these new endpoints for bids:
    # Using the singular 'bid' endpoint (what your frontend is currently trying to use)
    path('auctions/<uuid:auction_id>/bid/', api.place_bid, name='place-bid'),

    # Alternative plural 'bids' endpoint for RESTful consistency
    path('auctions/<uuid:auction_id>/bids/', BidViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='auction-bids'),

    # General bid creation endpoint
    path('bids/', api.place_bid, name='create-bid'),

    # Add these for bids:
    path('bids/', api.place_bid, name='place-bid'),  # General bid endpoint
    path('auctions/<uuid:auction_id>/bid/', api.place_bid, name='auction-specific-bid'),  # Auction-specific endpoint
]
