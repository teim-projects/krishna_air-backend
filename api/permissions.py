from rest_framework.permissions import BasePermission

class IsAdminOrSubAdmin(BasePermission):
    """
    Allow access to:
      - superuser (treated as admin)
      - users with role 'admin'
      - users with role 'sub-admin'
    Deny others.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        role_name = getattr(getattr(user, 'role', None), 'name', '') or ''
        return role_name.lower() in ('admin', 'sub-admin')
    

  
class StaffObjectPermission(BasePermission):
    """
    Object-level permissions:
      - superuser/admin (same power): full control (retrieve, update, delete)
      - sub-admin: can retrieve and update, but cannot delete
      - others: no object-level access
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # is admin-like (superuser or role == 'admin')
        role_name = getattr(getattr(user, 'role', None), 'name', '') or ''
        is_admin_like = user.is_superuser or role_name.lower() == 'admin'
        is_subadmin = role_name.lower() == 'sub-admin'

        # Admin-like: allow everything
        if is_admin_like:
            return True

        # Subadmin: allow GET, PUT, PATCH but NOT DELETE
        if is_subadmin:
            if request.method == 'DELETE':
                return False
            return True

        # Others: deny
        return False