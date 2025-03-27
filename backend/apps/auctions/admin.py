from django.contrib import admin
from .models import Category, Item, Auction, Bid, AuctionWatch


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ("bidder", "amount", "timestamp", "status")
    readonly_fields = ("timestamp",)


class AuctionWatchInline(admin.TabularInline):
    model = AuctionWatch
    extra = 0
    fields = ("user", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "description")
    search_fields = ("name", "description")
    list_filter = ("parent",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("name", "description", "owner__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "owner")}),
        ("Category & Images", {"fields": ("category", "image_urls")}),
        ("Item Details", {"fields": ("weight", "dimensions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "item",
        "seller",
        "starting_price",
        "status",
        "start_time",
        "end_time",
    )
    list_filter = ("status", "auction_type", "start_time", "end_time")
    search_fields = ("title", "description", "seller__email", "item__name")
    readonly_fields = ("created_at", "updated_at", "current_price", "total_bids", "id")
    fieldsets = (
        (None, {"fields": ("title", "description", "item", "seller")}),
        (
            "Pricing",
            {
                "fields": (
                    "starting_price",
                    "reserve_price",
                    "buy_now_price",
                    "current_price",
                )
            },
        ),
        (
            "Auction Details",
            {
                "fields": (
                    "auction_type",
                    "status",
                    "start_time",
                    "end_time",
                    "total_bids",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [BidInline, AuctionWatchInline]

    def current_price(self, obj):
        return obj.current_price

    def total_bids(self, obj):
        return obj.total_bids

    def get_fieldsets(self, request, obj=None):
        """
        Only show ID field when editing an existing object
        """
        fieldsets = super().get_fieldsets(request, obj)

        if obj:
            fieldsets = (
                (None, {"fields": ("id", "title", "description", "item", "seller")}),
            ) + fieldsets[1:]

        return fieldsets


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("bidder", "auction", "amount", "status", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("bidder__email", "auction__title")
    readonly_fields = ("timestamp",)


@admin.register(AuctionWatch)
class AuctionWatchAdmin(admin.ModelAdmin):
    list_display = ("user", "auction", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "auction__title")
    readonly_fields = ("created_at",)
