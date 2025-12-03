from dj_rest_auth.registration.serializers import RegisterSerializer 
from dj_rest_auth.serializers import LoginSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import serializers
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import CustomUser, Role
from rest_framework.exceptions import ValidationError

class CustomRegisterSerializer(RegisterSerializer):
    username = None  # disable username completely
    mobile_no = serializers.CharField(required=False, allow_blank=True, max_length=15)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['mobile_no'] = self.validated_data.get('mobile_no', '')
        return data

    def save(self, request):
        user = super().save(request)
        user.mobile_no = self.validated_data.get('mobile_no', '')
        user.save()
        return user


User = get_user_model()

class CustomLoginSerializer(LoginSerializer):
    username = None
    email_or_mobile = serializers.CharField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        email_or_mobile = attrs.get('email_or_mobile')
        password = attrs.get('password')

        if not email_or_mobile or not password:
            raise serializers.ValidationError("Both email/mobile and password are required.")

        user = authenticate(username=email_or_mobile, password=password)

        if not user:
            try:
                if '@' in email_or_mobile:
                    user = User.objects.get(email=email_or_mobile)
                else:
                    user = User.objects.get(mobile_no=email_or_mobile)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid credentials.")
            if not user.check_password(password):
                raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        attrs['user'] = user
        return attrs



class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'mobile_no', 'role',  'profile_photo')
        read_only_fields = ('email',)

    def to_internal_value(self, instance):
        internal = super().to_internal_value(instance)

        full_name = instance.get("full_name")
        if full_name:
            parts = full_name.strip().split()
            internal['first_name'] = parts[0]
            internal['last_name'] = ''.join(parts[1:]) if len(parts) > 1 else ""

        if "mobile_no" in instance:
            internal["mobile_no"] = str(instance["mobile_no"]).replace(" ", "").strip() 

        return internal       

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['full_name'] = f"{instance.first_name or ''} {instance.last_name or ''}"
        return rep
    


User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email.")
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)

        frontend_url = getattr(settings, "FRONTEND_URL", 
                            #    "http://localhost:5173/password-reset-confirm"
                            )
        reset_link = f"{frontend_url}/{uid}/{token}/"

        subject = "Password Reset Request"
        context = {"user": user, "reset_link": reset_link}
        body = render_to_string("registration/custom_password_reset_email.html", context)

        email = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        email.send()

        return {"detail": "Password reset email sent successfully."}


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        uidb64 = attrs.get("uidb64")
        token = attrs.get("token")
        new_password = attrs.get("new_password")

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uidb64": "Invalid UID."})

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            raise serializers.ValidationError({"token": "Invalid or expired token."})

        user.set_password(new_password)
        user.save()

        return {"detail": "Password has been reset successfully."}

# ---RoleSerializer----
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name')
        read_only_fields = ('id',)

# Staff Profile section
class RoleFlexibleField(serializers.RelatedField):
    """
    Accepts either:
      - integer id (e.g. 3)
      - string id (e.g. "3")
      - role name (e.g. "staff" or "Staff")
    Represents role in responses as {"id": id, "name": name}
    """
    def to_internal_value(self, data):
        # integer id or numeric string -> pk
        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            try:
                pk = int(data)
                return Role.objects.get(pk=pk)
            except Role.DoesNotExist:
                raise ValidationError(f"Role with id={data} does not exist.")
        # string -> treat as name (case-insensitive)
        if isinstance(data, str):
            try:
                return Role.objects.get(name__iexact=data)
            except Role.DoesNotExist:
                raise ValidationError(f"Role with name='{data}' does not exist.")
        raise ValidationError("Invalid role value. Provide a role id or name.")

    def to_representation(self, value):
        return {"id": value.id, "name": value.name}


class AddStaffSerializer(serializers.ModelSerializer):
    role = RoleFlexibleField(queryset=Role.objects.all(), required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'mobile_no', 'first_name', 'last_name', 'role', 'password')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('mobile_no'):
            raise serializers.ValidationError("Either email or mobile_no is required.")
        return attrs

    def _creator_is_admin_or_subadmin_or_super(self, creator):
        """
        Return True if the creator is superuser OR has role 'admin' OR has role 'subadmin'.
        These creators are allowed to assign ANY existing Role.
        """
        if creator is None:
            return False
        if getattr(creator, 'is_superuser', False):
            return True
        creator_role_name = getattr(getattr(creator, 'role', None), 'name', '') or ''
        return creator_role_name.lower() in ('admin', 'subadmin')

    def create(self, validated_data):
        request = self.context.get('request', None)
        creator = getattr(request, 'user', None)

        requested_role = validated_data.pop('role')  # Role instance from RoleFlexibleField
        password = validated_data.pop('password')

        # If creator is not admin/subadmin/superuser, block assignment (or adjust policy)
        if not self._creator_is_admin_or_subadmin_or_super(creator):
            raise ValidationError("You do not have permission to assign roles.")

        # Create user via manager (which can accept role instance)
        user = CustomUser.objects.create_user(role=requested_role, password=password, **validated_data)
        user.is_staff = True
        user.save()
        return user

    def update(self, instance, validated_data):
        """
        Update instance. If role is present, check creator permission and apply.
        Other fields updated normally. Password is supported here as well.
        """
        request = self.context.get('request', None)
        creator = getattr(request, 'user', None)

        # Role change requested?
        requested_role = validated_data.get('role', None)
        if requested_role is not None:
            # Only admin/subadmin/superuser allowed to change role to anything
            if not self._creator_is_admin_or_subadmin_or_super(creator):
                raise ValidationError("You do not have permission to change role.")
            instance.role = requested_role
            # remove from dict so loop below doesn't try to set it again
            validated_data.pop('role', None)

        # Password handling
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
    

