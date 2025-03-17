from django.urls import path
from .views import create_auction
from .views import auction_detail

urlpatterns = [
    path("create/", create_auction, name="create_auction"),
    path('<int:id>/', auction_detail, name='auction_detail'),
]
