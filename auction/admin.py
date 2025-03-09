from django.contrib import admin
from .models import Users, Categories, Items, Auctions, Bids, Transactions, Notifications

admin.site.register(Users)
admin.site.register(Categories)
admin.site.register(Items)
admin.site.register(Auctions)
admin.site.register(Bids)
admin.site.register(Transactions)
admin.site.register(Notifications)
