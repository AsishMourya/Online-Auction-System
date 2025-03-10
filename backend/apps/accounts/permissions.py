from functools import wraps
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.response import Response


class IsAdmin(BasePermission):
    """
    Permission check for admin users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsStaff(BasePermission):
    """
    Permission check for staff users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == "staff" or request.user.role == "admin"
        )


class IsSeller(BasePermission):
    """
    Permission check for seller users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "seller"


class IsBuyer(BasePermission):
    """
    Permission check for buyer users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "buyer"


class IsBidder(BasePermission):
    """
    Permission check for bidder users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "bidder"


def admin_required(view_func):
    """
    Decorator to require admin role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == "admin":
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "Admin privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper


def staff_required(view_func):
    """
    Decorator to require staff or admin role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == "staff" or request.user.role == "admin"
        ):
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "Staff privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper


def seller_required(view_func):
    """
    Decorator to require seller role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == "seller" or request.user.role == "admin"
        ):
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "Seller privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper


def buyer_required(view_func):
    """
    Decorator to require buyer role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == "buyer" or request.user.role == "admin"
        ):
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "Buyer privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper


def bidder_required(view_func):
    """
    Decorator to require bidder role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == "bidder" or request.user.role == "admin"
        ):
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "Bidder privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper
