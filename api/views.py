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
from .models import CustomUser, Role
from .serializers import AddStaffSerializer, RoleSerializer
from .permissions import IsAdminOrSubAdmin ,StaffObjectPermission
from .pagination import StaffPagination
from rest_framework.decorators import action
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


# Add Staff section

class StaffViewSet(viewsets.ModelViewSet):
    serializer_class = AddStaffSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSubAdmin, StaffObjectPermission]
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



from rest_framework.views import APIView

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = AddStaffSerializer(request.user)
        return Response(serializer.data)
