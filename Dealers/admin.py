from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Vehicle,
    VehicleImage,
    VehicleExpense,
    VehicleDocument,
)


# ==========================
# User Admin
# ==========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['email']

    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'role',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'email',
        'first_name',
        'last_name',
    )

    fieldsets = (
        (None, {
            'fields': (
                'email',
                'password',
            )
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name',
            )
        }),
        ('Permissions', {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Important Dates', {
            'fields': (
                'last_login',
                'created_at',
            )
        }),
    )

    readonly_fields = (
        'created_at',
        'last_login',
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'role',
                'password1',
                'password2',
            ),
        }),
    )


# ==========================
# Vehicle Admin
# ==========================
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'make',
        'model',
        'year',
        'selling_price',
        'final_price',
        'status',
        'uploaded_by',
        'created_at',
    )

    list_filter = (
        'status',
        'fuel_type',
        'transmission',
        'drive_type',
        'body_type',
        'year',
    )

    search_fields = (
        'make',
        'model',
        'vin',
        'engine_number',
    )

    ordering = (
        '-created_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'final_price',
        'total_expenses',
        'total_cost',
        'expected_profit',
        'profit_margin',
    )


# ==========================
# Vehicle Images
# ==========================
@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle',
        'is_cover',
        'order',
        'uploaded_at',
    )

    list_filter = (
        'is_cover',
    )

    ordering = (
        'vehicle',
        'order',
    )


# ==========================
# Vehicle Expenses
# ==========================
@admin.register(VehicleExpense)
class VehicleExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle',
        'expense_type',
        'amount',
        'date_incurred',
        'created_at',
    )

    list_filter = (
        'expense_type',
        'date_incurred',
    )

    search_fields = (
        'vehicle__make',
        'vehicle__model',
        'notes',
    )

    ordering = (
        '-date_incurred',
    )


# ==========================
# Vehicle Documents
# ==========================
@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle',
        'name',
        'is_partner_visible',
        'uploaded_at',
    )

    list_filter = (
        'is_partner_visible',
    )

    search_fields = (
        'vehicle__make',
        'vehicle__model',
        'name',
    )

    ordering = (
        '-uploaded_at',
    )