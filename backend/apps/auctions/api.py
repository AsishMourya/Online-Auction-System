from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Auction, Category, Bid
from .serializers import AuctionSerializer, CategorySerializer, BidSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_auctions(request):
    auctions = Auction.objects.filter(featured=True, status='active')
    serializer = AuctionSerializer(auctions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def place_bid(request, auction_id=None):
    """
    Place a bid on an auction
    """
    try:
        # Handle both URL and data-based auction_id
        if auction_id:
            auction = get_object_or_404(Auction, id=auction_id)
        else:
            auction_id = request.data.get('auction_id')
            if not auction_id:
                return Response(
                    {"success": False, "message": "Auction ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            auction = get_object_or_404(Auction, id=auction_id)
        
        # Check if auction is still active
        if auction.has_ended:
            return Response(
                {"success": False, "message": "This auction has ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get amount from request data
        amount = request.data.get('amount')
        if not amount:
            return Response(
                {"success": False, "message": "Bid amount is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return Response(
                {"success": False, "message": "Invalid bid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if amount is greater than current price + min increment
        min_valid_bid = auction.current_price + auction.min_bid_increment
        if amount < min_valid_bid:
            return Response(
                {
                    "success": False, 
                    "message": f"Bid must be at least ${min_valid_bid}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Create the bid
        bid = Bid.objects.create(
            auction=auction,
            bidder=request.user,
            amount=amount
        )
        
        # The save method of Bid will update the auction's current price
        
        serializer = BidSerializer(bid)
        return Response(
            {
                "success": True,
                "message": "Bid placed successfully",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )