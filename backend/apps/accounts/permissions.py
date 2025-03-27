from functools import wraps
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.response import Response


class IsAdmin(BasePermission):
    """
    Permission check for admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsStaff(BasePermission):
    """
    Permission check for staff users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["admin", "staff"]
        )


class IsUser(BasePermission):
    """
    Permission check for regular users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsOwner(BasePermission):
    """
    Permission to only allow owners of an object to access it.
    Assumes the model instance has an `user` attribute or is the user itself.
    """

    def has_object_permission(self, request, view, obj):
        if (
            hasattr(obj, "id")
            and hasattr(request.user, "id")
            and obj.id == request.user.id
        ):
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "owner"):
            return obj.owner == request.user

        if hasattr(obj, "seller"):
            return obj.seller == request.user

        if hasattr(obj, "bidder"):
            return obj.bidder == request.user

        if hasattr(obj, "recipient"):
            return obj.recipient == request.user

        return False


def admin_required(view_func):
    """
    Decorator for views that checks if the user is admin.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == "admin":
            return view_func(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapped_view


def staff_required(view_func):
    """
    Decorator for views that checks if the user is staff or admin.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ["admin", "staff"]:
            return view_func(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapped_view


def user_required(view_func):
    """
    Decorator for views that checks if the user is authenticated.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        return Response(
            {"detail": "Authentication required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return wrapped_view
