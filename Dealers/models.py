from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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


class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('draft',      'Draft'),       # NEW — internal prep, hidden from partners
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

    DRIVE_TYPE_CHOICES = [
        ('2wd', '2WD'),
        ('4wd', '4WD'),
        ('awd', 'AWD'),
    ]

    BODY_TYPE_CHOICES = [
        ('sedan',     'Sedan'),
        ('suv',       'SUV'),
        ('hatchback', 'Hatchback'),
        ('pickup',    'Pickup'),
        ('van',       'Van'),
        ('coupe',     'Coupe'),
        ('wagon',     'Wagon'),
        ('bus',       'Bus'),
    ]

    # ── Core identity ──────────────────────────────────────────────────────────
    make            = models.CharField(max_length=100)
    model           = models.CharField(max_length=100)
    year            = models.PositiveIntegerField()
    vin             = models.CharField(max_length=50, blank=True, help_text='VIN / Chassis number')
    engine_number   = models.CharField(max_length=50, blank=True)

    # ── Specs ──────────────────────────────────────────────────────────────────
    mileage         = models.PositiveIntegerField(help_text='Mileage in km')
    fuel_type       = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission    = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    engine_size     = models.CharField(max_length=20, blank=True)
    drive_type      = models.CharField(max_length=10, choices=DRIVE_TYPE_CHOICES, blank=True)
    body_type       = models.CharField(max_length=20, choices=BODY_TYPE_CHOICES, blank=True)
    seats           = models.PositiveIntegerField(null=True, blank=True)
    exterior_color  = models.CharField(max_length=50, blank=True)
    interior_color  = models.CharField(max_length=50, blank=True)

    # ── Features (stored as JSON list of strings) ──────────────────────────────
    features        = models.JSONField(default=list, blank=True)

    # ── Pricing (admin-only fields) ────────────────────────────────────────────
    purchase_price  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                          help_text='What the vehicle was bought for — never shown to partners')
    selling_price   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount        = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_value    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                          help_text='Estimated market / valuation value')

    # ── Valuation ──────────────────────────────────────────────────────────────
    valuation_date    = models.DateField(null=True, blank=True)
    valuation_company = models.CharField(max_length=100, blank=True)

    # ── Content ────────────────────────────────────────────────────────────────
    description     = models.TextField(blank=True)

    # ── Status & meta ──────────────────────────────────────────────────────────
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    uploaded_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='vehicles_uploaded'
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # Legacy field kept for backward compatibility (mirrors exterior_color)
    color           = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.year} {self.make} {self.model} — {self.status}'

    @property
    def final_price(self):
        """Selling price after discount."""
        if self.selling_price is None:
            return None
        if self.discount:
            return self.selling_price - self.discount
        return self.selling_price

    @property
    def total_expenses(self):
        return self.expenses.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def total_cost(self):
        if self.purchase_price is None:
            return None
        return self.purchase_price + self.total_expenses

    @property
    def expected_profit(self):
        if self.final_price is None or self.total_cost is None:
            return None
        return self.final_price - self.total_cost

    @property
    def profit_margin(self):
        if self.expected_profit is None or not self.total_cost:
            return None
        return round((self.expected_profit / self.total_cost) * 100, 1)

    # Partners see masked identifiers
    @property
    def vin_masked(self):
        if not self.vin:
            return ''
        return '*' * max(0, len(self.vin) - 4) + self.vin[-4:]

    @property
    def engine_number_masked(self):
        if not self.engine_number:
            return ''
        return '*' * max(0, len(self.engine_number) - 3) + self.engine_number[-3:]


class VehicleImage(models.Model):
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image       = models.ImageField()
    is_cover    = models.BooleanField(default=False)
    order       = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image for {self.vehicle} (cover={self.is_cover})'


class VehicleExpense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ('repainting',       'Repainting'),
        ('tyres',            'Tyres'),
        ('interior_repair',  'Interior Repair'),
        ('mechanical',       'Mechanical Repair'),
        ('spare_parts',      'Spare Parts'),
        ('bulbs',            'Bulbs'),
        ('bumper_repair',    'Bumper Repair'),
        ('transport',        'Transport'),
        ('detailing',        'Detailing'),
        ('labour',           'Labour'),
        ('miscellaneous',    'Miscellaneous'),
    ]

    vehicle      = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=30, choices=EXPENSE_TYPE_CHOICES)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    notes        = models.TextField(blank=True)
    date_incurred = models.DateField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_incurred', '-created_at']

    def __str__(self):
        return f'{self.get_expense_type_display()} — KES {self.amount} ({self.vehicle})'


class VehicleDocument(models.Model):
    vehicle            = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    name               = models.CharField(max_length=100, help_text='e.g. Valuation Report, Service History')
    file               = models.FileField(upload_to='vehicle_docs/')
    is_partner_visible = models.BooleanField(default=False,
                                              help_text='If true, partners can view/download this document')
    uploaded_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.vehicle})'