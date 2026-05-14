from rest_framework.permissions import BasePermission


class IsAdminOrSuperAdmin(BasePermission):
    """Only admin_staff and super_admin can access."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['super_admin', 'admin_staff']
        )


class IsSuperAdmin(BasePermission):
    """Only super_admin can access."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'super_admin'
        )