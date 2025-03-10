from rest_framework import serializers
from .models import UserRoles, User, ShippingAddress, PaymentMethod

class UserRolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoles
        fields = ['role_id', 'role_name', 'description']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role = UserRolesSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRoles.objects.all(), 
        source='role', 
        write_only=True
    )
    
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'password', 
            'first_name', 'last_name', 'role', 'role_id',
            'is_active', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at', 'is_active']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
        
    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            'address_id', 'user', 'address_line_1', 'address_line_2', 
            'city', 'state', 'zip_code', 'country', 
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['address_id', 'created_at', 'updated_at']

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'payment_id', 'user', 'payment_type', 
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_id', 'created_at', 'updated_at']