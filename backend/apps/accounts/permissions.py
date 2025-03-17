from functools import wraps
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


class IsUser(BasePermission):
    """
    Permission check for regular users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "user"


class IsOwner(BasePermission):
    """
    Permission check to ensure a user can only access their own data.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the object has a user attribute
        if hasattr(obj, "user"):
            return obj.user == request.user
        # If it's a user object, check the ID
        return obj == request.user


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


def user_required(view_func):
    """
    Decorator to require user role for a view function.
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == "user" or request.user.role == "admin"
        ):
            return view_func(self, request, *args, **kwargs)
        return Response(
            {"message": "User privileges required to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapper
