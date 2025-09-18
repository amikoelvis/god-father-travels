from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for all, write permissions only for admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == "admin"


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Authenticated users can write; others can read-only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: owners or admins can edit/delete.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        return getattr(obj, "user", None) == request.user


class IsCustomerOrAdmin(permissions.BasePermission):
    """
    Only customers or admins can access certain endpoints.
    Useful for bookings/payments/reviews.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["customer", "admin"]


class RoleBasedPermission(permissions.BasePermission):
    """
    Fine-grained role-based access:
    - SAFE_METHODS: anyone
    - Admins: create/update/delete
    - Staff/Customer: restricted by resource
    """
    admin_actions = ["create", "update", "partial_update", "destroy"]

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(request.user, "role"):
            if request.user.role == "admin":
                return True
            # optionally, add staff-only or customer-only logic here
        return False
