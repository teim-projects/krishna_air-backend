from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.

class CustomUserManager(BaseUserManager):
  def create_user(self, email=None, mobile_no = None, password = None, **extra_fields):
    if not email and not mobile_no:
      raise ValueError("User must have either an email or mobile number")
    
    if email:
      email = self.normalize_email(email)
      extra_fields['email'] = email

      user = self.model(mobile_no = mobile_no, **extra_fields)
      user.set_password(password)
      user.save(using=self._db)
      return user
    
  
  def create_superuser(self, email, mobile_no, password, **extra_fields):
    extra_fields.setdefault("is_staff",True)
    extra_fields.setdefault("is_superuser",True)
    extra_fields.setdefault("is_active",True)
    extra_fields.setdefault("role","admin")

    return self.create_user(email, mobile_no, password, **extra_fields)
  


# Custom user model 
class CustomUser(AbstractBaseUser, PermissionsMixin):
  ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    )
  username = None
  email = models.EmailField(unique=True, blank=True, null=True)
  mobile_no = models.CharField(max_length=15, unique=True, blank=True, null=True )
  first_name = models.CharField(max_length=100, blank=True)
  last_name = models.CharField(max_length=100, blank=True)
  role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="customer")
  profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)

  is_active = models.BooleanField(default=True)
  is_staff = models.BooleanField(default=False)
  date_joined = models.DateTimeField(auto_now_add=True)

  objects = CustomUserManager()

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = ['mobile_no']

  def __str__(self):
        return self.email if self.email else str(self.mobile_no)

