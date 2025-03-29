from rest_framework import serializers
from django.utils import timezone
from django.db import transaction

from apps.accounts.serializers import UserProfileBasicSerializer
from .models import Category, Item, Auction, Bid, AuctionWatch
from apps.transactions.models import AutoBid


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "parent"]


class ItemSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(read_only=True)
    owner_details = UserProfileBasicSerializer(source="owner", read_only=True)
    category_name = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "description",
            "image_urls",
            "category",
            "category_name",
            "owner_id",
            "owner_details",
            "weight",
            "dimensions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner_id", "created_at", "updated_at"]
        extra_kwargs = {
            "category": {"required": False},
        }

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["owner"] = user

        category_name = validated_data.pop("category_name", None)

        if "category" not in validated_data and category_name:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"Category for {category_name}"},
            )
            validated_data["category"] = category

        if "category" not in validated_data:
            raise serializers.ValidationError(
                {"category": "Either category or category_name must be provided."}
            )

        return super().create(validated_data)


class BidSerializer(serializers.ModelSerializer):
    bidder_id = serializers.UUIDField(read_only=True)
    bidder_details = UserProfileBasicSerializer(source="bidder", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    bidder_name = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            "id",
            "auction",
            "bidder",
            "bidder_id",
            "bidder_details",
            "bidder_name",
            "auction_title",
            "amount",
            "timestamp",
            "status",
        ]
        read_only_fields = ["id", "bidder", "bidder_id", "timestamp", "status"]

    def get_bidder_name(self, obj):
        return f"{obj.bidder.first_name} {obj.bidder.last_name}"

    def validate(self, data):
        user = self.context["request"].user
        auction = data.get("auction")

        if auction.seller == user:
            raise serializers.ValidationError("You cannot bid on your own auction.")

        if not auction.is_active():
            raise serializers.ValidationError("This auction is not active.")

        if auction.has_ended:
            raise serializers.ValidationError("This auction has ended")

        amount = data.get("amount")
        highest_bid = (
            auction.bids.filter(status=Bid.STATUS_ACTIVE).order_by("-amount").first()
        )
        min_bid = highest_bid.amount if highest_bid else auction.starting_price
        min_valid_bid = auction.current_price + auction.min_bid_increment

        if amount <= min_bid:
            raise serializers.ValidationError(
                f"Bid must be higher than the current highest bid of {min_bid}."
            )

        if amount < min_valid_bid:
            raise serializers.ValidationError(
                f"Bid must be at least ${min_valid_bid}"
            )

        from apps.accounts.models import Wallet

        try:
            wallet = Wallet.objects.get(user=user)
            if wallet.balance < amount:
                raise serializers.ValidationError("Insufficient funds in your wallet.")
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("You need to set up a wallet first.")

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["bidder"] = user
        return super().create(validated_data)


class AuctionSerializer(serializers.ModelSerializer):
    seller_id = serializers.UUIDField(read_only=True)
    seller_details = UserProfileBasicSerializer(source="seller", read_only=True)
    item_details = ItemSerializer(source="item", read_only=True)
    current_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_bids = serializers.IntegerField(read_only=True)
    time_remaining = serializers.DurationField(read_only=True)
    highest_bidder = UserProfileBasicSerializer(read_only=True)
    is_watched = serializers.SerializerMethodField()
    item_data = ItemSerializer(required=True, write_only=True)

    class Meta:
        model = Auction
        fields = [
            "id",
            "title",
            "description",
            "item_data",
            "item_details",
            "seller_id",
            "seller_details",
            "starting_price",
            "reserve_price",
            "buy_now_price",
            "current_price",
            "start_time",
            "end_time",
            "status",
            "auction_type",
            "total_bids",
            "time_remaining",
            "highest_bidder",
            "is_watched",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "seller_id",
            "current_price",
            "total_bids",
            "time_remaining",
            "highest_bidder",
            "is_watched",
            "created_at",
            "updated_at",
        ]

    def get_is_watched(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return AuctionWatch.objects.filter(user=request.user, auction=obj).exists()
        return False

    def validate(self, data):
        start_time = data.get("start_time", getattr(self.instance, "start_time", None))
        end_time = data.get("end_time", getattr(self.instance, "end_time", None))

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )

        starting_price = data.get(
            "starting_price", getattr(self.instance, "starting_price", 0)
        )
        reserve_price = data.get(
            "reserve_price", getattr(self.instance, "reserve_price", None)
        )
        buy_now_price = data.get(
            "buy_now_price", getattr(self.instance, "buy_now_price", None)
        )

        if starting_price <= 0:
            raise serializers.ValidationError(
                {"starting_price": "Starting price must be greater than zero."}
            )

        if reserve_price is not None:
            if reserve_price <= 0:
                raise serializers.ValidationError(
                    {"reserve_price": "Reserve price must be greater than zero."}
                )
            if reserve_price < starting_price:
                raise serializers.ValidationError(
                    {
                        "reserve_price": "Reserve price cannot be less than starting price."
                    }
                )

        if buy_now_price is not None:
            if buy_now_price <= 0:
                raise serializers.ValidationError(
                    {"buy_now_price": "Buy now price must be greater than zero."}
                )
            if reserve_price and buy_now_price <= reserve_price:
                raise serializers.ValidationError(
                    {
                        "buy_now_price": "Buy now price must be greater than reserve price."
                    }
                )
            elif not reserve_price and buy_now_price <= starting_price:
                raise serializers.ValidationError(
                    {
                        "buy_now_price": "Buy now price must be greater than starting price."
                    }
                )

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["seller"] = user

        item_data = validated_data.pop("item_data")
        item_data["owner"] = user

        category_name = item_data.pop("category_name", None)

        if "category" not in item_data and category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"Category for {category_name}"},
            )
            item_data["category"] = category

        if "category" not in item_data:
            category, _ = Category.objects.get_or_create(
                name="Uncategorized",
                defaults={"description": "Items without a specific category"},
            )
            item_data["category"] = category

        item = Item.objects.create(**item_data)
        validated_data["item"] = item

        with transaction.atomic():
            now = timezone.now()
            if validated_data.get("start_time") <= now:
                validated_data["status"] = Auction.STATUS_ACTIVE
            else:
                validated_data["status"] = Auction.STATUS_PENDING

            auction = super().create(validated_data)

        return auction

    def update(self, instance, validated_data):
        if instance.bids.exists():
            for field in ["starting_price", "reserve_price", "item"]:
                if field in validated_data:
                    raise serializers.ValidationError(
                        {field: f"Cannot modify {field} once bids have been placed."}
                    )

        if "status" in validated_data:
            if (
                instance.status != Auction.STATUS_DRAFT
                and validated_data["status"] != Auction.STATUS_CANCELLED
            ):
                raise serializers.ValidationError(
                    {
                        "status": "Can only change status to CANCELLED or if auction is in DRAFT state."
                    }
                )

        return super().update(instance, validated_data)


class AuctionWatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionWatch
        fields = ["id", "user", "auction", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class AuctionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating auctions with item data"""
    
    item_data = serializers.JSONField()
    
    # Add these fields with write_only=True since they're not in the model
    category_id = serializers.IntegerField(write_only=True)
    duration = serializers.IntegerField(write_only=True, required=False, default=7)
    
    class Meta:
        model = Auction
        fields = [
            'title', 'description', 'starting_price', 'min_bid_increment',
            'category_id', 'duration', 'item_data', 'start_time', 
            'end_time', 'auction_type'
        ]
        
    def create(self, validated_data):
        # Handle fields not on the model
        item_data = validated_data.pop('item_data', {})
        category_id = validated_data.pop('category_id', None)
        duration = validated_data.pop('duration', 7)
        
        # Handle start/end times
        if 'start_time' not in validated_data:
            validated_data['start_time'] = timezone.now()
            
        if 'end_time' not in validated_data:
            validated_data['end_time'] = validated_data['start_time'] + timezone.timedelta(days=duration)
        
        # Create the auction
        auction = Auction.objects.create(
            seller=validated_data.get('seller'),
            title=validated_data.get('title'),
            description=validated_data.get('description'),
            starting_price=validated_data.get('starting_price'),
            min_bid_increment=validated_data.get('min_bid_increment'),
            start_time=validated_data.get('start_time'),
            end_time=validated_data.get('end_time'),
            auction_type=validated_data.get('auction_type', 'standard')
        )
        
        # Create the item
        item = Item.objects.create(
            name=auction.title,
            description=auction.description,
            owner=auction.seller,
            condition=item_data.get('condition', 'new'),
            location=item_data.get('location', ''),
            category_id=category_id,  # This uses the category_id we extracted earlier
            auction=auction
        )
        
        return auction


class AutoBidSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoBid
        fields = ['id', 'user', 'auction', 'max_amount', 'bid_increment', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
