from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ─── USER MANAGER ────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'super_admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# ─── USER MODEL ──────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin_staff', 'Admin Staff'),
        ('sales_partner', 'Sales Partner'),
    ]

    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name  = models.CharField(max_length=50)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales_partner')
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def is_admin(self):
        return self.role in ['super_admin', 'admin_staff']

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'


# ─── VEHICLE MODEL ───────────────────────────────────────────────────────────

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('available',  'Available'),
        ('reserved',   'Reserved'),
        ('sold',       'Sold'),
    ]

    FUEL_CHOICES = [
        ('petrol',   'Petrol'),
        ('diesel',   'Diesel'),
        ('electric', 'Electric'),
        ('hybrid',   'Hybrid'),
    ]

    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual',    'Manual'),
    ]

    # Core info
    make         = models.CharField(max_length=100)
    model        = models.CharField(max_length=100)
    year         = models.PositiveIntegerField()
    price        = models.DecimalField(max_digits=12, decimal_places=2)

    # Specs
    mileage      = models.PositiveIntegerField(help_text='Mileage in km')
    fuel_type    = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    color        = models.CharField(max_length=50, blank=True)
    engine_size  = models.CharField(max_length=20, blank=True)

    # Extra details
    description  = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    # Tracking
    uploaded_by  = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicles_uploaded'
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.year} {self.make} {self.model} — {self.status}'


# ─── VEHICLE IMAGE MODEL ─────────────────────────────────────────────────────

class VehicleImage(models.Model):
    vehicle   = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image     = models.ImageField(upload_to='vehicles/')
    is_cover  = models.BooleanField(default=False)  # marks the main display image
    order     = models.PositiveIntegerField(default=0)  # controls display order
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image for {self.vehicle} (cover={self.is_cover})'