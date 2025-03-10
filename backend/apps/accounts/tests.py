from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import UserRoles, User, ShippingAddress, PaymentMethod

class UserModelTests(TestCase):
    def setUp(self):
        self.buyer_role = UserRoles.objects.create(
            role_name=UserRoles.BUYER,
            description="Regular buyer account"
        )
        
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
            role=self.buyer_role
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertTrue(user.check_password("password123"))
        
    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
            first_name="Admin"
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)

class ShippingAddressTests(TestCase):
    def setUp(self):
        self.buyer_role = UserRoles.objects.create(
            role_name=UserRoles.BUYER,
            description="Regular buyer account"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="password123",
            first_name="Test",
            role=self.buyer_role
        )
        
    def test_create_shipping_address(self):
        address = ShippingAddress.objects.create(
            user=self.user,
            address_line_1="123 Test St",
            city="Test City",
            state="Test State",
            zip_code="12345",
            country="Test Country",
            is_default=True
        )
        self.assertEqual(address.address_line_1, "123 Test St")
        self.assertEqual(address.user, self.user)