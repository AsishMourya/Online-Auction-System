from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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
def place_bid(request, auction_id):
    try:
        auction = Auction.objects.get(id=auction_id, status='active')
        amount = float(request.data.get('amount', 0))
        
        # Validate bid amount
        if amount <= auction.current_bid:
            return Response(
                {"error": f"Bid must be higher than current bid (${auction.current_bid})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create bid
        bid = Bid(
            auction=auction,
            bidder=request.user,
            amount=amount
        )
        bid.save()
        
        # Update auction current bid
        auction.current_bid = amount
        auction.save()
        
        return Response({"message": "Bid placed successfully"}, status=status.HTTP_201_CREATED)
    
    except Auction.DoesNotExist:
        return Response(
            {"error": "Auction not found or has ended"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )