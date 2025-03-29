from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import Auction, Category, Bid
from apps.transactions.models import Transaction, AutoBid
from .serializers import AuctionSerializer, CategorySerializer, BidSerializer, AutoBidSerializer
from apps.accounts.models import Wallet

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
    """
    Get a list of featured auctions (newest and with highest price)
    """
    try:
        # Get limit parameter, default to 3
        limit = int(request.query_params.get('limit', 3))
        
        # Get newest auctions with highest current price
        auctions = Auction.objects.filter(
            status=Auction.STATUS_ACTIVE,  
            end_time__gt=timezone.now()  
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

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def autobids(request):
    """
    GET: Retrieve autobid settings for a specific auction
    POST: Create or update autobid settings
    """
    if request.method == 'GET':
        auction_id = request.query_params.get('auction_id')
        if not auction_id:
            return Response({
                'success': False,
                'message': 'Auction ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            auto_bid = AutoBid.objects.get(
                user=request.user,
                auction_id=auction_id
            )
            serializer = AutoBidSerializer(auto_bid)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except AutoBid.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No auto-bid found for this auction'
            }, status=status.HTTP_404_NOT_FOUND)
            
    elif request.method == 'POST':
        auction_id = request.data.get('auction_id')
        max_amount = request.data.get('max_amount')
        bid_increment = request.data.get('bid_increment')
        is_active = request.data.get('is_active', True)
        
        if not auction_id or not max_amount or not bid_increment:
            return Response({
                'success': False,
                'message': 'Auction ID, max amount, and bid increment are required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            max_amount = Decimal(str(max_amount))
            bid_increment = Decimal(str(bid_increment))
        except:
            return Response({
                'success': False,
                'message': 'Invalid amount values'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Get the auction
        try:
            auction = Auction.objects.get(id=auction_id)
        except Auction.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Auction not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Check if the user has enough balance
        try:
            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < max_amount:
                return Response({
                    'success': False,
                    'message': 'Insufficient funds in wallet'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Wallet.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Create or update auto-bid
        auto_bid, created = AutoBid.objects.update_or_create(
            user=request.user,
            auction=auction,
            defaults={
                'max_amount': max_amount,
                'bid_increment': bid_increment,
                'is_active': is_active
            }
        )
        
        serializer = AutoBidSerializer(auto_bid)
        return Response({
            'success': True,
            'message': 'Auto-bidding settings saved successfully',
            'data': serializer.data
        })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_auto_bid(request):
    """Disable auto-bidding for a specific auction"""
    auction_id = request.data.get('auction_id')
    if not auction_id:
        return Response({
            'success': False,
            'message': 'Auction ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        auto_bid = AutoBid.objects.get(
            user=request.user,
            auction_id=auction_id
        )
        auto_bid.is_active = False
        auto_bid.save()
        
        return Response({
            'success': True,
            'message': 'Auto-bidding disabled successfully'
        })
    except AutoBid.DoesNotExist:
        return Response({
            'success': False,
            'message': 'No auto-bid found for this auction'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def auction_bids(request, auction_id):
    """Get bids for a specific auction - authenticated version"""
    try:
        auction = get_object_or_404(Auction, id=auction_id)
        # Check if user is allowed to see bids
        if auction.seller != request.user and not auction.is_public:
            return Response({
                'success': False,
                'message': 'Not authorized to view these bids'
            }, status=status.HTTP_403_FORBIDDEN)
            
        bids = Bid.objects.filter(auction=auction).order_by('-created_at')
        serializer = BidSerializer(bids, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_auction_bids(request, auction_id):
    """Get bids for a public auction - no authentication required"""
    try:
        auction = get_object_or_404(Auction, id=auction_id, is_public=True)
        bids = Bid.objects.filter(auction=auction).order_by('-created_at')
        serializer = BidSerializer(bids, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Auction.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Auction not found or not public'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def place_bid(request, auction_id):
    """Place a bid on an auction"""
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        
        if amount <= 0:
            return Response({
                'success': False,
                'message': 'Bid amount must be greater than zero'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Get the auction
        auction = get_object_or_404(Auction, id=auction_id)
        
        # Check if auction is open for bidding
        if not auction.is_active:
            return Response({
                'success': False,
                'message': 'This auction is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if auction.end_time < timezone.now():
            return Response({
                'success': False,
                'message': 'This auction has ended'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if user is owner of the auction
        if auction.seller == request.user:
            return Response({
                'success': False,
                'message': 'You cannot bid on your own auction'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if bid is high enough
        current_price = auction.current_price or auction.starting_price
        min_bid = current_price + auction.min_bid_increment
        
        if amount < min_bid:
            return Response({
                'success': False,
                'message': f'Bid must be at least ${min_bid}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if user has enough balance
        try:
            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < amount:
                return Response({
                    'success': False,
                    'message': 'Insufficient funds in wallet'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Wallet.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Create the bid with transaction
        with transaction.atomic():
            # Hold the funds
            wallet.balance -= amount
            wallet.held_balance += amount
            wallet.save()
            
            # Create a hold transaction
            hold_transaction = Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TYPE_BID_HOLD,
                amount=amount,
                status=Transaction.STATUS_COMPLETED,
                description=f"Hold for bid on {auction.title}",
                completed_at=timezone.now(),
                reference_id=auction.id
            )
            
            # Create the bid
            bid = Bid.objects.create(
                auction=auction,
                bidder=request.user,
                amount=amount,
                transaction=hold_transaction
            )
            
            # Update auction current price
            auction.current_price = amount
            auction.save()
            
        # Return response
        return Response({
            'success': True,
            'message': 'Bid placed successfully',
            'data': {
                'bid_id': str(bid.id),
                'amount': float(amount),
                'created_at': bid.created_at.isoformat()
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error placing bid: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)