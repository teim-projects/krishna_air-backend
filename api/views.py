from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token  # type: ignore
from google.auth.transport import requests  # type: ignore
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView 
from rest_framework import viewsets
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
import os
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import CustomUser, Role, BranchManagement, SiteManagement, RolePermission
from .serializers import AddStaffSerializer, RoleSerializer, BranchSerializers, SiteSerializers, RolePermissionSerializer
from .permissions import IsAdminOrSubAdmin, StaffObjectPermission, HasDocPermission
from .pagination import StaffPagination
from .mixins import OptionalAllPaginationMixin
from rest_framework.decorators import action
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
User = get_user_model()

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    # callback_url = "http://127.0.0.1:8000/accounts/google/login/callback/"
    callback_url = os.getenv('GOOGLE_CALLBACK_URL')

    def post(self, request, *args, **kwargs):
        """
        Verify Google token → get/create user → issue JWT tokens.
        """
        token = request.data.get("access_token")
        if not token:
            return Response({"error": "Missing access_token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                os.getenv('GOOGLE_CLIENT_ID')
                # "129181997839-0rlmm080229tetuka9c0i83la4r4lhdt.apps.googleusercontent.com"
            )

            email = idinfo.get("email")
            name = idinfo.get("name", "")
            picture = idinfo.get("picture", "")

            # ✅ Get or create user
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.is_active = True
                if hasattr(user, "full_name"):
                    user.full_name = name
                if hasattr(user, "profile_photo") and picture:
                    user.profile_photo = picture
                user.save()

            # ✅ Generate JWT tokens for this user
            refresh = RefreshToken.for_user(user)
            data = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": user.email,
                "name": name,
                "message": "Google login successful"
            }

            return Response(data, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"error": "Invalid Google token", "details": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# Custom password reset and set password 

class PasswordResetRequestView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password reset email sent."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


# Role section
class RoleViewSet(viewsets.ModelViewSet):
    """
    CRUD for Role model.
    Only accessible to admin/subadmin or superuser.
    """
    queryset = Role.objects.all().order_by('id')
    serializer_class = RoleSerializer
    authentication_classes = [JWTAuthentication]   
    permission_classes = [IsAuthenticated, IsAdminOrSubAdmin]
    pagination_class = None


# Role Permission section
class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    CRUD for RolePermission model.
    Only accessible to admin/subadmin or superuser.
    """
    queryset = RolePermission.objects.all().order_by('document_type', 'role__name')
    serializer_class = RolePermissionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrSubAdmin]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['role', 'document_type']
    search_fields = ['document_type', 'role__name']

    @action(detail=False, methods=['post'], url_path='restore-defaults')
    def restore_defaults(self, request):
        """
        Populate default standard permission rules for common roles if empty.
        """
        roles = Role.objects.all()
        doc_types = [
            "Customer", "Lead", "Quotation", "Invoice",
            "Item Master", "High Side", "Low Side", "Installation Work",
            "Inventory", "Purchase Order (PO)", "GRN", "Material Issue", "Material Return", "Delivery Challan",
            "AMC", "Service Management",
            "Accounts", "Branch", "Site", "Role Permissions"
        ]
        created_count = 0
        for r in roles:
            for dt in doc_types:
                obj, created = RolePermission.objects.get_or_create(
                    role=r,
                    document_type=dt,
                    defaults={
                        'read_permission': True,
                        'write_permission': r.name.lower() in ['admin', 'manager', 'sales manager'],
                        'create_permission': r.name.lower() in ['admin', 'manager', 'sales manager'],
                        'delete_permission': r.name.lower() in ['admin'],
                        'export_permission': True,
                        'import_permission': r.name.lower() in ['admin', 'manager'],
                        'view_all_permission': r.name.lower() in ['admin', 'manager'],
                        'modify_all_permission': r.name.lower() in ['admin'],
                    }
                )
                if created:
                    created_count += 1
        return Response({"detail": f"Restored default permissions. Created {created_count} rules."}, status=status.HTTP_200_OK)


# Add Staff section

class StaffViewSet(viewsets.ModelViewSet):
    serializer_class = AddStaffSerializer
    document_type = "Accounts"
    permission_classes = [IsAuthenticated, HasDocPermission]
    authentication_classes = [JWTAuthentication]  
    pagination_class = StaffPagination 
    filter_backends = [DjangoFilterBackend , filters.SearchFilter]
    search_fields = ['^first_name', '=email', 'mobile_no','role__name']
    filterset_fields = ['role']

    def get_queryset(self):
        return CustomUser.objects.filter(is_staff=True)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'], url_path='all' , permission_classes=[IsAuthenticated])
    def all_staff(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            
            # Build response manually to avoid serializer issues
            data = {
                'id': user.id,
                'email': user.email,
                'mobile_no': user.mobile_no or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'address': user.address or '',
                'city': user.city or '',
                'state': user.state or '',
                'pincode': user.pincode or '',
                'date_of_joining': user.date_of_joining,
                'role': None,
            }
            
            # Add role if it exists
            if user.role:
                data['role'] = {
                    'id': user.role.id,
                    'name': user.role.name
                }
            
            # Determine if admin
            role = user.role
            is_admin = bool(user.is_superuser or (role and role.name.lower() in ['admin', 'sub-admin', 'administrator', 'super admin', 'superadmin']))
            
            # Fetch permissions if role exists
            permissions_list = []
            permissions_version = 1
            
            if role and role.id:
                perms = RolePermission.objects.filter(role=role)
                permissions_list = RolePermissionSerializer(perms, many=True).data
                
                # Try to get permissions version from cache, but handle Redis connection errors gracefully
                try:
                    permissions_version = cache.get(f'role_permissions_version_{role.id}', 1)
                except Exception:
                    # If cache is unavailable, just use default version
                    permissions_version = 1
            
            data['is_admin'] = is_admin
            data['permissions'] = permissions_list
            data['permissions_version'] = permissions_version
            
            return Response(data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in MeView.get(): {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to fetch user info", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# --------------------------------------------------------------------------------
# Branch Management Viewsets
# --------------------------------------------------------------------------------

class BranchManagementViewSet(OptionalAllPaginationMixin, viewsets.ModelViewSet):
    queryset = BranchManagement.objects.all()
    serializer_class = BranchSerializers
    document_type = "Branch"
    authentication_classes = [JWTAuthentication]   
    permission_classes = [IsAuthenticated, HasDocPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        'name', '=email', 'primary_contact',
        'city', 'state',
    ]
    filterset_fields = ['city', 'state']


# --------------------------------------------------------------------------------
# Site Management Viewsets
# --------------------------------------------------------------------------------

class SiteManagementViewSet(OptionalAllPaginationMixin, viewsets.ModelViewSet):
    queryset = SiteManagement.objects.all()
    serializer_class = SiteSerializers
    document_type = "Site"
    authentication_classes = [JWTAuthentication]   
    permission_classes = [IsAuthenticated, HasDocPermission]
    filter_backends = [ filters.SearchFilter]
    search_fields = [
        'name',"pincode","owner_contact","owner_name",
        'city', 'state',
    ]


# ==================== CACHE INVALIDATION SIGNALS ====================
# When RolePermission is modified, invalidate the cache for that role
# so that the next API call will return fresh permissions

@receiver(post_save, sender=RolePermission)
def invalidate_role_permissions_on_save(sender, instance, **kwargs):
    """Invalidate cache when a role permission is created or updated"""
    try:
        cache.delete(f'role_permissions_version_{instance.role.id}')
        # Increment version to force frontend refresh
        current_version = cache.get(f'role_permissions_version_{instance.role.id}', 0)
        cache.set(f'role_permissions_version_{instance.role.id}', current_version + 1, timeout=None)
    except Exception:
        # If cache is unavailable, just continue - permissions will be fetched fresh next time
        pass


@receiver(post_delete, sender=RolePermission)
def invalidate_role_permissions_on_delete(sender, instance, **kwargs):
    """Invalidate cache when a role permission is deleted"""
    try:
        cache.delete(f'role_permissions_version_{instance.role.id}')
        # Increment version to force frontend refresh
        current_version = cache.get(f'role_permissions_version_{instance.role.id}', 0)
        cache.set(f'role_permissions_version_{instance.role.id}', current_version + 1, timeout=None)
    except Exception:
        # If cache is unavailable, just continue - permissions will be fetched fresh next time
        pass