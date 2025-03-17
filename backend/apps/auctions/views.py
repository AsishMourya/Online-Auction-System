from django.db import transaction
from django.utils import timezone
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.permissions import IsAdmin
from apps.transactions.models import AutoBid, Wallet
from apps.transactions.serializers import AutoBidSerializer
from .models import Category, Item, Auction, Bid, AuctionWatch
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    AuctionSerializer,
    BidSerializer,
)
from apps.core.mixins import SwaggerSchemaMixin


class CategoryViewSet(viewsets.ModelViewSet):
    """API endpoints for managing categories"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_permissions(self):
        """Only admins can create, update or delete categories"""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated, IsAdmin]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    @swagger_auto_schema(
        operation_id="list_categories",
        operation_summary="List categories",
        operation_description="Get all auction categories",
        tags=["Categories"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="create_category",
        operation_summary="Create category",
        operation_description="Create a new category (Admin only)",
        tags=["Categories"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="retrieve_category",
        operation_summary="Get category",
        operation_description="Get details of a specific category",
        tags=["Categories"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="update_category",
        operation_summary="Update category",
        operation_description="Update a category (Admin only)",
        tags=["Categories"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="delete_category",
        operation_summary="Delete category",
        operation_description="Delete a category (Admin only)",
        tags=["Categories"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class AuctionViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for managing auctions"""

    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "auction_type", "seller"]
    search_fields = ["title", "description", "item__name"]
    ordering_fields = ["start_time", "end_time", "starting_price", "current_price"]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        """Return all active auctions + user's own auctions"""
        user = self.request.user

        if self.action in ["list", "retrieve"]:
            return Auction.objects.filter(
                Q(status=Auction.STATUS_ACTIVE) | Q(seller=user)
            ).select_related("seller", "item")

        return Auction.objects.filter(seller=user)

    def get_permissions(self):
        """Only allow users to update or delete their own auctions"""
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

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

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
                "item": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description="Existing item ID (optional if item_data is provided)",
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
                            description="New category name (optional if category is provided)",
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
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="retrieve_auction",
        operation_summary="Get auction details",
        operation_description="Get details for a specific auction",
        tags=["Auctions"],
        responses={200: AuctionSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
            return Response(
                {"detail": "You do not have permission to update this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.status != Auction.STATUS_DRAFT and auction.bids.exists():
            return Response(
                {"detail": "Cannot update auction that has bids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)

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
            return Response(
                {"detail": "You do not have permission to delete this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.bids.exists():
            return Response(
                {"detail": "Cannot delete auction that has bids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)

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
            return Response(
                {"detail": "You do not have permission to cancel this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auction.status in [Auction.STATUS_ENDED, Auction.STATUS_SOLD]:
            return Response(
                {"detail": "Cannot cancel an ended auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auction.status = Auction.STATUS_CANCELLED
        auction.save()

        auction.bids.filter(status=Bid.STATUS_ACTIVE).update(
            status=Bid.STATUS_CANCELLED
        )

        serializer = self.get_serializer(auction)
        return Response(serializer.data)

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
            return Response(
                {"detail": "Cannot watch your own auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if AuctionWatch.objects.filter(user=user, auction=auction).exists():
            return Response(
                {"detail": "Already watching this auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        watch = AuctionWatch.objects.create(user=user, auction=auction)

        return Response(
            {"detail": "Auction added to watchlist."}, status=status.HTTP_201_CREATED
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
            return Response(
                {"detail": "Auction removed from watchlist."}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Auction was not in watchlist."},
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
        return Response(serializer.data)

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
        return Response(serializer.data)


class BidViewSet(viewsets.ModelViewSet):
    """API endpoints for auction bids"""

    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return all bids for auctions the user has bid on, or all bids for user's auctions"""
        user = self.request.user

        if self.action == "list":
            queryset = Bid.objects.filter(bidder=user)

            auction_id = self.request.query_params.get("auction")
            if auction_id:
                auction = get_object_or_404(Auction, id=auction_id)

                if user == auction.seller or user.role == "admin":
                    return Bid.objects.filter(auction=auction)
                else:
                    return Bid.objects.filter(auction=auction, bidder=user)

            return queryset

        return Bid.objects.all()

    def get_permissions(self):
        """Only allow read access to bids"""
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated, IsAdmin]
        return super().get_permissions()

    @swagger_auto_schema(
        operation_id="list_bids",
        operation_summary="List bids",
        operation_description="Get bids placed by current user or all bids for an auction if user is seller",
        tags=["Bids"],
        responses={200: BidSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="create_bid",
        operation_summary="Place bid",
        operation_description="Place a new bid on an auction",
        tags=["Bids"],
        responses={201: BidSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            with transaction.atomic():
                bid = serializer.save()

                auction = bid.auction
                if auction.buy_now_price and bid.amount >= auction.buy_now_price:
                    auction.status = Auction.STATUS_SOLD
                    auction.save()

                    bid.status = Bid.STATUS_WON
                    bid.save()

                    auction.bids.exclude(id=bid.id).update(status=Bid.STATUS_LOST)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id="retrieve_bid",
        operation_summary="Get bid details",
        operation_description="Get details for a specific bid",
        tags=["Bids"],
        responses={200: BidSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="get_my_bids",
        operation_summary="Get my bids",
        operation_description="Get all bids placed by current user",
        tags=["Bids"],
        responses={200: BidSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def my_bids(self, request):
        user = request.user
        queryset = Bid.objects.filter(bidder=user)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
    return Response(serializer.data)


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

    return Response(response_data)


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
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
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
    return Response({"categories": serializer.data})


class AutoBidViewSet(SwaggerSchemaMixin, viewsets.ModelViewSet):
    """API endpoints for managing automatic bidding"""

    serializer_class = AutoBidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.is_swagger_request:
            return self.get_swagger_empty_queryset()

        """Return autobids for the current user"""
        return AutoBid.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_id="list_autobids",
        operation_summary="List autobids",
        operation_description="Get all autobid settings for the current user",
        tags=["AutoBids"],
        responses={200: AutoBidSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
                return Response(
                    {"detail": "Insufficient funds in wallet for maximum bid amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Wallet.DoesNotExist:
            return Response(
                {"detail": "You need to create a wallet first."},
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
        return Response(
            result_serializer.data,
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
        return Response(serializer.data)

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
        return Response(serializer.data)
