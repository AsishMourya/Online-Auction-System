import csv
from datetime import datetime
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from .models import Auction, Bid
from .serializers import (
    AuctionSerializer,
    BidSerializer,
)


class AdminAuctionViewSet(viewsets.ModelViewSet):
    """Admin API for managing auctions"""

    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_id="admin_list_auctions",
        operation_summary="List all auctions (Admin)",
        operation_description="Admin access to list all auctions with filtering options",
        tags=["Admin - Auctions"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        seller_id = request.query_params.get("seller")
        if seller_id:
            queryset = queryset.filter(seller__id=seller_id)

        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"message": "Auctions retrieved successfully", "auctions": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_retrieve_auction",
        operation_summary="Get auction details (Admin)",
        operation_description="Admin access to get detailed auction information",
        tags=["Admin - Auctions"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Auction details retrieved successfully",
                "auction": serializer.data,
            }
        )

    @swagger_auto_schema(
        operation_id="admin_update_auction",
        operation_summary="Update auction (Admin)",
        operation_description="Admin can update any auction details",
        tags=["Admin - Auctions"],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {"message": "Auction updated successfully", "auction": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_verify_auction",
        operation_summary="Verify auction (Admin)",
        operation_description="Admin can verify an auction to ensure it meets marketplace standards",
        tags=["Admin - Auctions"],
        responses={200: "Auction verified", 400: "Bad request", 404: "Not found"},
    )
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Mark an auction as verified by admin"""
        auction = self.get_object()

        if auction.status not in [Auction.STATUS_PENDING, Auction.STATUS_DRAFT]:
            return Response(
                {"detail": "Only pending or draft auctions can be verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        if now >= auction.start_time:
            auction.status = Auction.STATUS_ACTIVE
        else:
            auction.status = Auction.STATUS_PENDING

        auction.save()

        serializer = self.get_serializer(auction)
        return Response(
            {"message": "Auction verified successfully", "auction": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_cancel_auction",
        operation_summary="Cancel auction (Admin)",
        operation_description="Admin can cancel any auction",
        tags=["Admin - Auctions"],
        responses={200: "Auction cancelled", 400: "Bad request", 404: "Not found"},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an auction as admin"""
        auction = self.get_object()

        if auction.status in [
            Auction.STATUS_ENDED,
            Auction.STATUS_SOLD,
            Auction.STATUS_CANCELLED,
        ]:
            return Response(
                {
                    "detail": "Cannot cancel an already ended, sold, or cancelled auction."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        auction.status = Auction.STATUS_CANCELLED
        auction.save()

        auction.bids.filter(status=Bid.STATUS_ACTIVE).update(
            status=Bid.STATUS_CANCELLED
        )

        serializer = self.get_serializer(auction)
        return Response(
            {"message": "Auction cancelled successfully", "auction": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_auction_analytics",
        operation_summary="Auction analytics (Admin)",
        operation_description="Get detailed analytics for a specific auction",
        tags=["Admin - Auctions"],
        responses={200: "Analytics data", 404: "Not found"},
    )
    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        """Get detailed analytics for an auction"""
        auction = self.get_object()

        total_bids = auction.bids.count()
        unique_bidders = auction.bids.values("bidder").distinct().count()
        bid_amounts = auction.bids.order_by("-amount").values_list("amount", flat=True)

        highest_bid = bid_amounts.first() if bid_amounts else auction.starting_price
        avg_bid = sum(bid_amounts) / len(bid_amounts) if bid_amounts else 0

        bid_timestamps = auction.bids.order_by("timestamp").values(
            "timestamp", "amount"
        )

        watchers_count = auction.watchers.count()

        return Response(
            {
                "auction_id": auction.id,
                "title": auction.title,
                "start_time": auction.start_time,
                "end_time": auction.end_time,
                "status": auction.status,
                "starting_price": auction.starting_price,
                "current_price": auction.current_price,
                "analytics": {
                    "total_bids": total_bids,
                    "unique_bidders": unique_bidders,
                    "highest_bid": highest_bid,
                    "average_bid": avg_bid,
                    "bid_history": list(bid_timestamps),
                    "watchers_count": watchers_count,
                },
            }
        )


class AdminBidViewSet(viewsets.ModelViewSet):
    """Admin API for managing bids"""

    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_id="admin_list_bids",
        operation_summary="List all bids (Admin)",
        operation_description="Admin access to list all bids with filtering options",
        tags=["Admin - Bids"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        bidder_id = request.query_params.get("bidder")
        if bidder_id:
            queryset = queryset.filter(bidder__id=bidder_id)

        auction_id = request.query_params.get("auction")
        if auction_id:
            queryset = queryset.filter(auction__id=auction_id)

        min_amount = request.query_params.get("min_amount")
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)

        max_amount = request.query_params.get("max_amount")
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)

        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"message": "Bids retrieved successfully", "bids": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_retrieve_bid",
        operation_summary="Get bid details (Admin)",
        operation_description="Admin access to get detailed bid information",
        tags=["Admin - Bids"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "Bid details retrieved successfully", "bid": serializer.data}
        )

    @swagger_auto_schema(
        operation_id="admin_update_bid",
        operation_summary="Update bid (Admin)",
        operation_description="Admin can update any bid details",
        tags=["Admin - Bids"],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Bid updated successfully", "bid": serializer.data})

    @swagger_auto_schema(
        operation_id="admin_cancel_bid",
        operation_summary="Cancel bid (Admin)",
        operation_description="Admin can cancel any bid",
        tags=["Admin - Bids"],
        responses={200: "Bid cancelled", 400: "Bad request", 404: "Not found"},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a bid as admin"""
        bid = self.get_object()

        if bid.status != Bid.STATUS_ACTIVE:
            return Response(
                {"detail": "Only active bids can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bid.status = Bid.STATUS_CANCELLED
        bid.save()

        if bid.auction.highest_bidder == bid.bidder:
            next_highest_bid = (
                bid.auction.bids.exclude(id=bid.id)
                .filter(status=Bid.STATUS_OUTBID)
                .order_by("-amount")
                .first()
            )
            if next_highest_bid:
                next_highest_bid.status = Bid.STATUS_ACTIVE
                next_highest_bid.save()

        serializer = self.get_serializer(bid)
        return Response(
            {"message": "Bid cancelled successfully", "bid": serializer.data}
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_auction_dashboard",
    operation_summary="Auction Dashboard (Admin)",
    operation_description="Get auction statistics for admin dashboard",
    tags=["Admin - Dashboard"],
    responses={200: "Dashboard data", 403: "Permission Denied"},
)
def admin_auction_dashboard(request):
    """Admin dashboard with auction statistics"""
    now = timezone.now()

    total_auctions = Auction.objects.count()
    active_auctions = Auction.objects.filter(status=Auction.STATUS_ACTIVE).count()
    ended_auctions = Auction.objects.filter(status=Auction.STATUS_ENDED).count()
    sold_auctions = Auction.objects.filter(status=Auction.STATUS_SOLD).count()
    total_bids = Bid.objects.count()

    status_stats = Auction.objects.values("status").annotate(count=Count("id"))

    today_auctions = Auction.objects.filter(created_at__date=now.date()).count()
    today_bids = Bid.objects.filter(timestamp__date=now.date()).count()

    ending_soon = Auction.objects.filter(
        status=Auction.STATUS_ACTIVE, end_time__lte=now + timezone.timedelta(hours=24)
    ).count()

    recent_auctions = Auction.objects.filter(
        created_at__gte=now - timezone.timedelta(days=7)
    ).order_by("-created_at")[:5]
    recent_bids = Bid.objects.filter(
        timestamp__gte=now - timezone.timedelta(days=7)
    ).order_by("-timestamp")[:5]

    recent_auction_data = AuctionSerializer(recent_auctions, many=True).data
    recent_bid_data = BidSerializer(recent_bids, many=True).data

    return Response(
        {
            "overall_stats": {
                "total_auctions": total_auctions,
                "active_auctions": active_auctions,
                "ended_auctions": ended_auctions,
                "sold_auctions": sold_auctions,
                "total_bids": total_bids,
            },
            "status_breakdown": list(status_stats),
            "today_stats": {
                "auctions_created": today_auctions,
                "bids_placed": today_bids,
            },
            "ending_soon_count": ending_soon,
            "recent_activity": {
                "auctions": recent_auction_data,
                "bids": recent_bid_data,
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_export_auctions",
    operation_summary="Export auctions (Admin)",
    operation_description="Export auctions data to CSV",
    tags=["Admin - Data Export"],
    responses={200: "CSV file", 403: "Permission Denied"},
)
def admin_export_auctions(request):
    """Export auctions data to CSV"""
    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = (
        f'attachment; filename="auctions_export_{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Title",
            "Item Name",
            "Seller",
            "Starting Price",
            "Current Price",
            "Reserve Price",
            "Buy Now Price",
            "Status",
            "Start Time",
            "End Time",
            "Total Bids",
            "Created At",
        ]
    )

    auctions = Auction.objects.all().select_related("seller", "item")

    for auction in auctions:
        writer.writerow(
            [
                auction.id,
                auction.title,
                auction.item.name,
                auction.seller.email,
                auction.starting_price,
                auction.current_price,
                auction.reserve_price or "N/A",
                auction.buy_now_price or "N/A",
                auction.get_status_display(),
                auction.start_time,
                auction.end_time,
                auction.bids.count(),
                auction.created_at,
            ]
        )

    return response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_export_bids",
    operation_summary="Export bids (Admin)",
    operation_description="Export bids data to CSV",
    tags=["Admin - Data Export"],
    responses={200: "CSV file", 403: "Permission Denied"},
)
def admin_export_bids(request):
    """Export bids data to CSV"""
    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = (
        f'attachment; filename="bids_export_{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        ["ID", "Auction Title", "Bidder Email", "Amount", "Status", "Timestamp"]
    )

    bids = Bid.objects.all().select_related("auction", "bidder")

    for bid in bids:
        writer.writerow(
            [
                bid.id,
                bid.auction.title,
                bid.bidder.email,
                bid.amount,
                bid.get_status_display(),
                bid.timestamp,
            ]
        )

    return response


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_verify_auction",
    operation_summary="Verify auction (Admin)",
    operation_description="Verify an auction after review",
    tags=["Admin - Auctions"],
    responses={200: "Auction verified", 400: "Bad request", 404: "Not found"},
)
def admin_verify_auction(request, auction_id):
    """Verify an auction after admin review"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        return Response(
            {"detail": "Auction not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if auction.status not in [Auction.STATUS_PENDING, Auction.STATUS_DRAFT]:
        return Response(
            {"detail": "Only pending or draft auctions can be verified."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    if now >= auction.start_time:
        auction.status = Auction.STATUS_ACTIVE
    else:
        auction.status = Auction.STATUS_PENDING

    auction.save()

    serializer = AuctionSerializer(auction)
    return Response(
        {"message": "Auction verified successfully", "auction": serializer.data}
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@swagger_auto_schema(
    operation_id="admin_hide_auction",
    operation_summary="Hide auction (Admin)",
    operation_description="Hide an auction from the marketplace",
    tags=["Admin - Auctions"],
    responses={200: "Auction hidden", 400: "Bad request", 404: "Not found"},
)
def admin_hide_auction(request, auction_id):
    """Hide an auction from the marketplace"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        return Response(
            {"detail": "Auction not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if auction.status == Auction.STATUS_CANCELLED:
        return Response(
            {"detail": "Auction is already cancelled/hidden."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    auction.status = Auction.STATUS_CANCELLED
    auction.save()

    auction.bids.filter(status=Bid.STATUS_ACTIVE).update(status=Bid.STATUS_CANCELLED)

    serializer = AuctionSerializer(auction)
    return Response(
        {"message": "Auction hidden successfully", "auction": serializer.data}
    )
