from django.db import transaction
from django.utils import timezone
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.urls import get_resolver
from django.http import JsonResponse

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.permissions import IsAdmin
from apps.transactions.models import AutoBid
from apps.accounts.models import Wallet
from apps.transactions.serializers import AutoBidSerializer
from apps.core.mixins import SwaggerSchemaMixin, ApiResponseMixin
from apps.core.responses import api_response

from .models import Category, Item, Auction, Bid, AuctionWatch
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    AuctionSerializer,
    BidSerializer,
    AuctionCreateSerializer  # Add this import
)


class CategoryViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    """API endpoints for managing categories"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Allow anyone to view categories
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_permissions(self):
        """Only admins can create, update or delete categories, anyone can view"""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated, IsAdmin]
        else:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    @swagger_auto_schema(
        operation_id="list_categories",
        operation_summary="List categories",
        operation_description="Get all auction categories",
        tags=["Categories"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data, message="Categories retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="create_category",
        operation_summary="Create category",
        operation_description="Create a new category (Admin only)",
        tags=["Categories"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return api_response(
            data=serializer.data,
            message="Category created successfully",
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_id="retrieve_category",
        operation_summary="Get category",
        operation_description="Get details of a specific category",
        tags=["Categories"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            data=serializer.data, message="Category details retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="update_category",
        operation_summary="Update category",
        operation_description="Update a category (Admin only)",
        tags=["Categories"],
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(
            data=serializer.data, message="Category updated successfully"
        )

    @swagger_auto_schema(
        operation_id="delete_category",
        operation_summary="Delete category",
        operation_description="Delete a category (Admin only)",
        tags=["Categories"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(message="Category deleted successfully")


class AuctionViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for managing auctions"""

    serializer_class = AuctionSerializer
    # Change permission to AllowAny for list and retrieve
    permission_classes = [permissions.AllowAny]

    # Update the get_permissions method
    def get_permissions(self):
        """Only require authentication for creating, updating, deleting auctions"""
        if self.action in ["create", "update", "partial_update", "destroy", "my_auctions", "watch", "unwatch", "watched"]:
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    # Update the get_queryset method
    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        """Return all active auctions + user's own auctions if authenticated"""
        user = self.request.user

        # For unauthenticated users, only show active auctions
        if not user.is_authenticated:
            return Auction.objects.filter(status=Auction.STATUS_ACTIVE).select_related("seller", "item")

        # For authenticated users, also show their own auctions
        if self.action in ["list", "retrieve"]:
            return Auction.objects.filter(
                Q(status=Auction.STATUS_ACTIVE) | Q(seller=user)
            ).select_related("seller", "item")

        return Auction.objects.filter(seller=user)

    @swagger_auto_schema(
        operation_id="list_auctions",
        operation_summary="List auctions",
        operation_description="Get all active auctions + user's own auctions",
        tags=["Auctions"],
        responses={200: AuctionSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(item__category=category)

        min_price = request.query_params.get("min_price")
        if min_price:
            queryset = queryset.filter(starting_price__gte=min_price)

        max_price = request.query_params.get("max_price")
        if max_price:
            queryset = queryset.filter(starting_price__lte=max_price)

        ending_soon = request.query_params.get("ending_soon")
        if ending_soon and ending_soon.lower() == "true":
            end_soon_threshold = timezone.now() + timezone.timedelta(hours=24)
            queryset = queryset.filter(end_time__lte=end_soon_threshold)

        featured = request.query_params.get('featured', None)
        if featured and featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': {
                'auctions': serializer.data,
                'count': queryset.count()
            }
        })

    @swagger_auto_schema(
        operation_id="create_auction",
        operation_summary="Create auction with item",
        operation_description="Create a new auction with item details",
        tags=["Auctions"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "title": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Auction title"
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Auction description"
                ),
                "item_data": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "name": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Item name"
                        ),
                        "description": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Item description"
                        ),
                        "category": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_UUID,
                            description="Category ID",
                        ),
                        "category_name": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="New category name (if category is not provided)",
                        ),
                        "image_urls": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="Item image URLs",
                        ),
                        "weight": openapi.Schema(
                            type=openapi.TYPE_NUMBER,
                            description="Item weight in kg (optional)",
                        ),
                        "dimensions": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Item dimensions (optional)",
                        ),
                    },
                    required=["name", "description"],
                ),
                "starting_price": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Starting price"
                ),
                "reserve_price": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Reserve price (optional)"
                ),
                "buy_now_price": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Buy now price (optional)"
                ),
                "start_time": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATETIME,
                    description="Start time",
                ),
                "end_time": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATETIME,
                    description="End time",
                ),
                "auction_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["standard", "reserve", "buy_now_only"],
                    description="Auction type",
                ),
            },
            required=[
                "title",
                "description",
                "item_data",
                "starting_price",
                "start_time",
                "end_time",
                "auction_type",
            ],
        ),
        responses={201: AuctionSerializer},
        security=[{"Bearer": []}],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return api_response(
            data=serializer.data,
            message="Auction created successfully",
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_id="retrieve_auction",
        operation_summary="Get auction details",
        operation_description="Get details for a specific auction",
        tags=["Auctions"],
        responses={200: AuctionSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            data=serializer.data, message="Auction details retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="update_auction",
        operation_summary="Update auction",
        operation_description="Update an existing auction (only owner)",
        tags=["Auctions"],
        responses={200: AuctionSerializer},
    )
    def update(self, request, *args, **kwargs):
        auction = self.get_object()

        if auction.seller != request.user:
            return api_response(
                success=False,
                message="Permission denied",
                errors={"detail": "You do not have permission to update this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.status != Auction.STATUS_DRAFT and auction.bids.exists():
            return api_response(
                success=False,
                message="Cannot update auction with bids",
                errors={"detail": "Cannot update auction that has bids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(auction, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(
            data=serializer.data, message="Auction updated successfully"
        )

    @swagger_auto_schema(
        operation_id="delete_auction",
        operation_summary="Delete auction",
        operation_description="Delete an auction (only owner and if no bids)",
        tags=["Auctions"],
        responses={204: "No content"},
    )
    def destroy(self, request, *args, **kwargs):
        auction = self.get_object()

        if auction.seller != request.user:
            return api_response(
                success=False,
                message="Permission denied",
                errors={"detail": "You do not have permission to delete this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.bids.exists():
            return api_response(
                success=False,
                message="Cannot delete auction with bids",
                errors={"detail": "Cannot delete auction that has bids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auction.delete()
        return api_response(message="Auction deleted successfully")

    @swagger_auto_schema(
        operation_id="cancel_auction",
        operation_summary="Cancel auction",
        operation_description="Cancel an active auction (only owner)",
        tags=["Auctions"],
        responses={200: AuctionSerializer},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        auction = self.get_object()

        if auction.seller != request.user:
            return api_response(
                success=False,
                message="Permission denied",
                errors={"detail": "You do not have permission to cancel this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.status in [Auction.STATUS_ENDED, Auction.STATUS_SOLD]:
            return api_response(
                success=False,
                message="Cannot cancel ended auction",
                errors={"detail": "Cannot cancel an ended auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auction.status = Auction.STATUS_CANCELLED
        auction.save()

        auction.bids.filter(status=Bid.STATUS_ACTIVE).update(
            status=Bid.STATUS_CANCELLED
        )

        serializer = self.get_serializer(auction)
        return api_response(
            data=serializer.data, message="Auction cancelled successfully"
        )

    @swagger_auto_schema(
        operation_id="watch_auction",
        operation_summary="Watch auction",
        operation_description="Add auction to user's watch list",
        tags=["Auctions"],
        responses={201: "Auction added to watchlist"},
    )
    @action(detail=True, methods=["post"])
    def watch(self, request, pk=None):
        auction = self.get_object()
        user = request.user

        if auction.seller == user:
            return api_response(
                success=False,
                message="Cannot watch own auction",
                errors={"detail": "Cannot watch your own auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if AuctionWatch.objects.filter(user=user, auction=auction).exists():
            return api_response(
                success=False,
                message="Already watching this auction",
                errors={"detail": "Already watching this auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        watch = AuctionWatch.objects.create(user=user, auction=auction)
        return api_response(
            message="Auction added to watchlist", status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_id="unwatch_auction",
        operation_summary="Unwatch auction",
        operation_description="Remove auction from user's watch list",
        tags=["Auctions"],
        responses={200: "Auction removed from watchlist"},
    )
    @action(detail=True, methods=["post"])
    def unwatch(self, request, pk=None):
        auction = self.get_object()
        user = request.user

        watch = AuctionWatch.objects.filter(user=user, auction=auction).first()
        if watch:
            watch.delete()
            return api_response(message="Auction removed from watchlist")
        else:
            return api_response(
                success=False,
                message="Auction was not in watchlist",
                errors={"detail": "Auction was not in watchlist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        operation_id="get_watched_auctions",
        operation_summary="Get watched auctions",
        operation_description="Get all auctions on user's watch list",
        tags=["Auctions"],
        responses={200: AuctionSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def watched(self, request):
        user = request.user
        watched_auction_ids = AuctionWatch.objects.filter(user=user).values_list(
            "auction_id", flat=True
        )
        queryset = Auction.objects.filter(id__in=watched_auction_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data, message="Watched auctions retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="get_my_auctions",
        operation_summary="Get my auctions",
        operation_description="Get all auctions created by current user",
        tags=["Auctions"],
        responses={200: AuctionSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def my_auctions(self, request):
        user = request.user
        queryset = Auction.objects.filter(seller=user)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data, message="Your auctions retrieved successfully"
        )


class BidViewSet(viewsets.ModelViewSet):
    """ViewSet for managing bids"""
    serializer_class = BidSerializer
    
    def get_permissions(self):
        """Allow anyone to view bids, but only authenticated users can create them"""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()
        
    def get_queryset(self):
        """Filter bids by auction_id if provided"""
        queryset = Bid.objects.all()
        auction_id = self.request.query_params.get('auction_id')
        if auction_id:
            queryset = queryset.filter(auction_id=auction_id)
        return queryset
        
    def perform_create(self, serializer):
        """Set the bidder to the current user"""
        serializer.save(bidder=self.request.user)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_id="search_auctions",
    operation_summary="Search auctions",
    operation_description="Search for auctions by keyword, category, price range, etc.",
    tags=["Auctions"],
)
def search_auctions(request):
    """Search for auctions with various filters"""
    queryset = Auction.objects.filter(status=Auction.STATUS_ACTIVE)

    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(item__name__icontains=search)
            | Q(item__description__icontains=search)
        )

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(item__category=category)

    min_price = request.query_params.get("min_price")
    if min_price:
        queryset = queryset.filter(starting_price__gte=min_price)

    max_price = request.query_params.get("max_price")
    if max_price:
        queryset = queryset.filter(starting_price__lte=max_price)

    sort = request.query_params.get("sort", "newest")
    if sort == "newest":
        queryset = queryset.order_by("-created_at")
    elif sort == "ending_soon":
        queryset = queryset.order_by("end_time")
    elif sort == "price_low":
        queryset = queryset.order_by("starting_price")
    elif sort == "price_high":
        queryset = queryset.order_by("-starting_price")

    serializer = AuctionSerializer(queryset, many=True, context={"request": request})
    return api_response(
        data=serializer.data, message="Search results retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_id="get_auction_stats",
    operation_summary="Get auction statistics",
    operation_description="Get statistics about a specific auction",
    tags=["Auctions"],
)
def auction_stats(request, auction_id):
    """Get statistics about an auction"""
    auction = get_object_or_404(Auction, id=auction_id)

    total_bids = auction.bids.count()
    unique_bidders = auction.bids.values("bidder").distinct().count()
    highest_bid = (
        auction.bids.aggregate(max_bid=Max("amount"))["max_bid"]
        or auction.starting_price
    )

    is_seller_or_admin = request.user == auction.seller or request.user.role == "admin"

    response_data = {
        "auction_id": auction.id,
        "title": auction.title,
        "current_price": auction.current_price,
        "total_bids": total_bids,
        "unique_bidders": unique_bidders,
        "highest_bid": highest_bid,
        "time_remaining": auction.time_remaining,
        "status": auction.status,
    }

    if is_seller_or_admin:
        bids = auction.bids.all().order_by("-timestamp")
        bid_serializer = BidSerializer(bids, many=True)
        response_data["bid_history"] = bid_serializer.data

    return api_response(
        data=response_data, message="Auction statistics retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_id="search_items",
    operation_summary="Search my items",
    operation_description="Search for user's own items by keyword, category, etc.",
    tags=["Items"],
    manual_parameters=[
        openapi.Parameter(
            "query",
            openapi.IN_QUERY,
            description="Search query",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "category",
            openapi.IN_QUERY,
            description="Filter by category ID",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
        ),
    ],
    responses={200: ItemSerializer(many=True)},
    security=[{"Bearer": []}],
)
def search_items(request):
    """Search for user's items with various filters"""
    user = request.user

    if user.role == "admin":
        queryset = Item.objects.all()
    else:
        queryset = Item.objects.filter(owner=user)

    query = request.query_params.get("query")
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    serializer = ItemSerializer(queryset, many=True)
    return api_response(data=serializer.data, message="Items retrieved successfully")


@api_view(["GET"])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
@swagger_auto_schema(
    operation_id="list_all_categories",
    operation_summary="List all categories",
    operation_description="Get a list of all available categories",
    tags=["Categories"],
    responses={200: CategorySerializer(many=True)},
)
def list_all_categories(request):
    """Get all categories"""
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return api_response(
        data={"categories": serializer.data},
        message="All categories retrieved successfully",
    )


class AutoBidViewSet(ApiResponseMixin, SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for managing automatic bidding"""

    serializer_class = AutoBidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AutoBid.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_id="list_autobids",
        operation_summary="List autobids",
        operation_description="Get all autobid settings for the current user",
        tags=["AutoBids"],
        responses={200: AutoBidSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data, message="AutoBids retrieved successfully"
        )

    @swagger_auto_schema(
        operation_id="create_autobid",
        operation_summary="Create autobid",
        operation_description="Set up automatic bidding for an auction",
        tags=["AutoBids"],
        responses={201: AutoBidSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auction_id = serializer.validated_data.get("auction").id
        max_amount = serializer.validated_data.get("max_amount")

        try:
            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < max_amount:
                return api_response(
                    success=False,
                    message="Insufficient funds",
                    errors={
                        "detail": "Insufficient funds in wallet for maximum bid amount."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Wallet.DoesNotExist:
            return api_response(
                success=False,
                message="Wallet required",
                errors={"detail": "You need to create a wallet first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        autobid, created = AutoBid.objects.update_or_create(
            user=request.user,
            auction_id=auction_id,
            defaults={
                "max_amount": max_amount,
                "bid_increment": serializer.validated_data.get("bid_increment", 1.00),
                "is_active": True,
            },
        )

        result_serializer = self.get_serializer(autobid)
        return api_response(
            data=result_serializer.data,
            message="AutoBid created successfully"
            if created
            else "AutoBid updated successfully",
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_id="deactivate_autobid",
        operation_summary="Deactivate autobid",
        operation_description="Deactivate automatic bidding for an auction",
        tags=["AutoBids"],
        responses={200: AutoBidSerializer},
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        autobid = self.get_object()
        autobid.is_active = False
        autobid.save()

        serializer = self.get_serializer(autobid)
        return api_response(
            data=serializer.data, message="AutoBid deactivated successfully"
        )

    @swagger_auto_schema(
        operation_id="activate_autobid",
        operation_summary="Activate autobid",
        operation_description="Activate automatic bidding for an auction",
        tags=["AutoBids"],
        responses={200: AutoBidSerializer},
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        autobid = self.get_object()
        autobid.is_active = True
        autobid.save()

        serializer = self.get_serializer(autobid)
        return api_response(
            data=serializer.data, message="AutoBid activated successfully"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    """Simple endpoint to test if authentication is working"""
    return Response({
        'success': True,
        'message': 'Authentication successful',
        'user_id': request.user.id,
        'username': request.user.username
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_auction(request):
    try:
        # Debug logging
        print(f"Creating auction. User: {request.user.id}")
        print(f"Request data: {request.data}")
        
        # Process the request and create auction
        serializer = AuctionCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            auction = serializer.save(seller=request.user)
            
            # Success response
            return Response({
                'success': True,
                'message': 'Auction created successfully',
                'data': AuctionSerializer(auction).data
            }, status=status.HTTP_201_CREATED)
        else:
            # Validation error response
            print(f"Validation errors: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Validation error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Unexpected error
        print(f"Error creating auction: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'success': False,
            'message': 'Error',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_auction_detail(request, auction_id):
    """
    Get auction details without requiring authentication
    """
    try:
        auction = Auction.objects.get(id=auction_id)
        serializer = AuctionSerializer(auction)
        return Response(serializer.data)
    except Auction.DoesNotExist:
        return Response({"detail": "Auction not found"}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_test(request):
    """
    Simple endpoint to test public access
    """
    return Response({
        'success': True,
        'message': 'Public API access is working'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_test(request):
    """Simple endpoint to test API functionality"""
    return Response({
        'success': True,
        'message': 'API is working properly',
        'endpoints': {
            'featured_auctions': '/api/v1/auctions/featured/',
            'auctions': '/api/v1/auctions/auctions/',
            'categories': '/api/v1/auctions/categories/',
            'debug_urls': '/api/v1/auctions/debug-urls/'
        }
    })


def debug_urls(request):
    """
    Debug view that returns all registered URLs in the project.
    This helps diagnose routing issues.
    """
    resolver = get_resolver()
    url_patterns = {}
    
    def collect_patterns(resolver_or_pattern, namespace=''):
        patterns = []
        
        if hasattr(resolver_or_pattern, 'url_patterns'):
            for pattern in resolver_or_pattern.url_patterns:
                patterns.extend(collect_patterns(pattern, namespace))
        elif hasattr(resolver_or_pattern, 'lookup_str'):
            # ViewPattern - CBV
            patterns.append({
                'pattern': str(resolver_or_pattern.pattern),
                'name': resolver_or_pattern.name,
                'lookup_str': resolver_or_pattern.lookup_str,
                'namespace': namespace
            })
        elif hasattr(resolver_or_pattern, 'callback'):
            # RegexPattern - FBV
            patterns.append({
                'pattern': str(resolver_or_pattern.pattern),
                'name': resolver_or_pattern.name,
                'callback': resolver_or_pattern.callback.__name__,
                'namespace': namespace
            })
        elif hasattr(resolver_or_pattern, 'namespace') and resolver_or_pattern.namespace:
            # URLResolver with namespace
            namespace = resolver_or_pattern.namespace
            for pattern in resolver_or_pattern.url_patterns:
                patterns.extend(collect_patterns(pattern, namespace))
        
        return patterns
    
    # Collect all URL patterns
    all_patterns = collect_patterns(resolver)
    
    # Return as JSON response
    return JsonResponse({
        'urls': all_patterns,
        'count': len(all_patterns)
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_auto_bid(request):
    """Disable auto-bidding for a specific auction"""
    try:
        auction_id = request.data.get('auction_id')
        if not auction_id:
            return Response({
                'success': False,
                'message': 'Auction ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Find the auto-bid for this user and auction
        auto_bid = AutoBid.objects.filter(
            user=request.user,
            auction_id=auction_id,
            is_active=True
        ).first()
        
        if not auto_bid:
            return Response({
                'success': False,
                'message': 'No active auto-bid found for this auction'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Disable the auto-bid
        auto_bid.is_active = False
        auto_bid.save()
        
        return Response({
            'success': True,
            'message': 'Auto-bidding disabled successfully'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error disabling auto-bid: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def featured_auctions(request):
    """
    Get a list of featured auctions (newest active auctions)
    """
    try:
        # Get limit parameter, default to 3
        limit = int(request.query_params.get('limit', 3))
        
        # Get current time
        now = timezone.now()
        
        # Get newest active auctions
        auctions = Auction.objects.filter(
            status=Auction.STATUS_ACTIVE,
            end_time__gt=now
        ).order_by('-created_at')[:limit]
        
        serializer = AuctionSerializer(auctions, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Add this simple view to test if your auctions can be accessed:
from django.http import JsonResponse
from .models import Auction, Category
from django.core.serializers import serialize
import json

def auctions_api_test(request):
    """Simple endpoint to test if auctions are in the database"""
    auctions = Auction.objects.all()[:10]  # Get up to 10 auctions
    auction_count = Auction.objects.count()
    
    categories = Category.objects.all()
    category_count = Category.objects.count()
    
    # Serialize the auctions to JSON
    auctions_data = json.loads(serialize('json', auctions))
    formatted_auctions = []
    
    for auction in auctions_data:
        # Extract the model fields
        fields = auction['fields']
        # Add the primary key
        fields['id'] = auction['pk']
        formatted_auctions.append(fields)
    
    # Serialize categories
    categories_data = json.loads(serialize('json', categories))
    formatted_categories = []
    
    for category in categories_data:
        fields = category['fields']
        fields['id'] = category['pk']
        formatted_categories.append(fields)
    
    return JsonResponse({
        'success': True,
        'data': {
            'auction_count': auction_count,
            'auctions': formatted_auctions,
            'category_count': category_count,
            'categories': formatted_categories
        }
    })
