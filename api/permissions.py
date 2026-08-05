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


class HasDocPermission(BasePermission):
    """
    Checks RolePermission table based on view's document_type attribute.
    If the doc_type has no permission or all permissions are OFF,
    falls back to checking the parent module permission.
    """

    # Parent module map — child doc_type → parent doc_type
    PARENT_MAP = {
        'purchase order (po)': 'Inventory',
        'grn':              'Inventory',
        'material issue':   'Inventory',
        'material return':  'Inventory',
        'delivery challan': 'Inventory',
        'high side':        'Item Master',
        'low side':         'Item Master',
        'installation work':'Item Master',
        'service management': 'AMC',
    }

    # URL fallback map (for views without document_type set)
    URL_PARENT_MAP = {
        '/inventory/purchase-orders': 'Purchase Order (PO)',
        '/inventory/grn': 'GRN',
        '/inventory/material-issue': 'Material Issue',
        '/inventory/material-returns': 'Material Return',
        '/inventory/inventory': 'Inventory',
        '/inventory/delivery-challan': 'Delivery Challan',
        '/inventory/terms': 'Inventory',
        '/amc/service-records': 'Service Management',
        '/amc/service-materials': 'Service Management',
        '/amc/service-visits': 'AMC',
        '/amc/technician-work-records': 'Service Management',
        '/product/': 'Item Master',
    }

    def _resolve_doc_type(self, view, request):
        doc_type = getattr(view, 'document_type', None)
        if doc_type:
            return doc_type
        path = request.path
        for prefix, parent in self.URL_PARENT_MAP.items():
            if path.startswith(prefix):
                return parent
        return None

    def _check_perm(self, perm, method):
        """Check specific action permission on a perm row."""
        if method in ('GET', 'HEAD', 'OPTIONS'):
            return perm.read_permission
        elif method == 'POST':
            return perm.create_permission
        elif method in ('PUT', 'PATCH'):
            return perm.write_permission
        elif method == 'DELETE':
            return perm.delete_permission
        return False

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        role_name = getattr(getattr(user, 'role', None), 'name', '') or ''
        if user.is_superuser or role_name.lower() in ('admin', 'sub-admin', 'administrator', 'super admin'):
            return True

        doc_type = self._resolve_doc_type(view, request)
        if not doc_type:
            return True

        user_role = user.role
        if not user_role:
            return False

        from .models import RolePermission

        # Check own permission row first
        perm = RolePermission.objects.filter(role=user_role, document_type__iexact=doc_type).first()

        if perm and self._check_perm(perm, request.method):
            return True

        # Own permission is OFF — check if parent module allows it
        parent_doc_type = self.PARENT_MAP.get(doc_type.lower())
        if parent_doc_type:
            parent_perm = RolePermission.objects.filter(
                role=user_role, document_type__iexact=parent_doc_type
            ).first()
            if parent_perm and self._check_perm(parent_perm, request.method):
                return True

        return False
