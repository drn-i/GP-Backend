from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# 1. PERMISSIONS TABLE
class Permission(models.Model):
    permission_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.permission_name

# 2. ROLES TABLE
class Role(models.Model):
    role_name = models.CharField(max_length=50, unique=True)
    
    # "Many-to-Many" creates the bridge table (ROLE_PERMISSIONS) automatically
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.role_name

# 3. MANAGER (Handles creating users)
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        
        # We assume Firebase handles the real password, but Django still needs this
        # if you want to log into the Admin Panel.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

# 4. USERS TABLE
class User(AbstractBaseUser, PermissionsMixin):
    # Diagram Fields - FIXED: Made optional so the /sync endpoint doesn't crash
    first_name = models.CharField(max_length=50, blank=True, null=True)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True, max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # The 'has' relationship (Foreign Key to Role)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Helper Fields (For Firebase & Django Admin)
    # We keep 'username' to store the Firebase UID securely
    username = models.CharField(max_length=150, unique=True, blank=True, null=True) 
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) # Required for Admin Panel access

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    # FIXED: Removed name fields so createsuperuser works smoothly
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email