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
    create_auction,
    public_auction_detail,
    public_test,
    debug_urls,
    api_test,
    featured_auctions,  # Add this import
    auctions_api_test  # Add this import
)
from . import api
from .api import disable_auto_bid

# Set up router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'auctions', AuctionViewSet, basename='auction')
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'autobids', AutoBidViewSet, basename='autobid')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    path('search/', search_auctions, name='search-auctions'),
    path('items/search/', search_items, name='search-items'),
    path('categories/all/', list_all_categories, name='list-all-categories'),
    path('test-auth/', test_auth, name='test-auth'),
    path('create-auction/', create_auction, name='create-auction'),
    path('test/', api_test, name='api-test'),    
    path('debug-urls/', debug_urls, name='debug-urls'),    
    path('auctions/<uuid:auction_id>/stats/', auction_stats, name='auction-stats'),
    path('auctions/<uuid:auction_id>/bid/', api.place_bid, name='place-bid'),
    path('auctions/<uuid:auction_id>/bids/', api.auction_bids, name='auction-bids'),
    
    # Auto-bid endpoints
    path('autobids/', api.autobids, name='autobids'),
    path('autobids/disable/', disable_auto_bid, name='disable-auto-bid'),
    
    # Public endpoints
    path('public/auctions/<uuid:auction_id>/', public_auction_detail, name='public-auction-detail'),
    path('public/auctions/<uuid:auction_id>/bids/', api.public_auction_bids, name='public-auction-bids'),
    path('public/test/', public_test, name='public-test'),

    # Featured auctions endpoint
    path('featured/', featured_auctions, name='featured-auctions'),

    # API test endpoint
    path('api/test/', auctions_api_test, name='auctions_api_test'),
]
