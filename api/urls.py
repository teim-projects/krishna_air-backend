
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import GoogleLogin ,PasswordResetRequestView, PasswordResetConfirmView, StaffViewSet,RoleViewSet,RolePermissionViewSet,MeView, BranchManagementViewSet , SiteManagementViewSet, NotificationViewSet, EmailTemplateViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'roles', RoleViewSet, basename='roles') 
router.register(r'role-permissions', RolePermissionViewSet, basename='role-permissions')
router.register(r'branch',BranchManagementViewSet, basename='branch')
router.register(r'site', SiteManagementViewSet, basename='sites')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'email-templates', EmailTemplateViewSet, basename='email-templates')

urlpatterns = [
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
     path("me/", MeView.as_view(), name="me"),
]

urlpatterns += router.urls