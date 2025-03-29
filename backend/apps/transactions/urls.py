from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('deposit/', views.deposit_funds, name='deposit-funds'),
    path('quick-deposit/', views.quick_deposit, name='quick-deposit'),
    path('account/balance/', views.get_account_balance, name='account-balance'),
]
