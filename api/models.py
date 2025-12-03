from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def _resolve_role(self, role):
        """
        Accepts None, Role instance, role name (str) or pk (int/str).
        Returns a Role instance or None.
        """
        if role is None:
            return None

        # If already a Role instance
        from .models import Role  # local import to avoid circular issues at import time
        if isinstance(role, Role):
            return role

        # If passed a string, treat it as name
        if isinstance(role, str):
            # try numeric pk first
            if role.isdigit():
                try:
                    return Role.objects.get(pk=int(role))
                except Role.DoesNotExist:
                    pass
            # fallback: get_or_create by name
            role_obj, _ = Role.objects.get_or_create(name=role)
            return role_obj

        # If passed an int (pk)
        if isinstance(role, int):
            return Role.objects.get(pk=role)

        # otherwise error
        raise ValueError("Invalid role value")

    def create_user(self, email=None, mobile_no=None, password=None, role=None, **extra_fields):
        if not email and not mobile_no:
            raise ValueError("User must have either an email or mobile number")

        user_data = {}
        if email:
            email = self.normalize_email(email)
            user_data['email'] = email

        if mobile_no:
            user_data['mobile_no'] = mobile_no

        # boolean flags can be passed via extra_fields (is_staff, is_superuser, is_active)
        # Remove role from extra_fields so we handle it separately
        extra_role = role if role is not None else extra_fields.pop('role', None)

        user = self.model(**user_data, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # If explicitly no password provided, set unusable password
            user.set_unusable_password()

        # Resolve and assign role
        role_obj = self._resolve_role(extra_role)
        user.role = role_obj

        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, mobile_no=None, password=None, **extra_fields):
        """
        Note: Django's `createsuperuser` management command will call this.
        Make sure USERNAME_FIELD handling aligns with your admin/createsuperuser usage.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # allow passing role as string or Role instance in extra_fields
        role = extra_fields.pop("role", "admin")  # default to "admin" if not passed

        return self.create_user(email=email, mobile_no=mobile_no, password=password, role=role, **extra_fields)


# Custome Roles 
class Role(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name 
    

# Custom user model 
class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True, blank=True, null=True)
    mobile_no = models.CharField(max_length=15, unique=True, blank=True, null=True )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['mobile_no']

    def __str__(self):
        identity = self.email if self.email else (self.mobile_no or "Anonymous")
        role_name = self.role.name if self.role else "NoRole"
        return f"{identity} - {role_name}"
