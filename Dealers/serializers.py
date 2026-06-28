from rest_framework import serializers
from .models import User, Vehicle, VehicleImage, VehicleExpense, VehicleDocument


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_active']

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'role', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# ─── VEHICLE IMAGE ────────────────────────────────────────────────────────────

class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VehicleImage
        fields = ['id', 'image', 'is_cover', 'order', 'uploaded_at']


# ─── VEHICLE EXPENSE ──────────────────────────────────────────────────────────

class VehicleExpenseSerializer(serializers.ModelSerializer):
    expense_type_display = serializers.CharField(
        source='get_expense_type_display', read_only=True
    )

    class Meta:
        model  = VehicleExpense
        fields = [
            'id', 'expense_type', 'expense_type_display',
            'amount', 'notes', 'date_incurred', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ─── VEHICLE DOCUMENT ─────────────────────────────────────────────────────────

class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VehicleDocument
        fields = ['id', 'name', 'file', 'is_partner_visible', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


# ─── VEHICLE LIST — compact, used in inventory grid ──────────────────────────
# Partners see this; draft vehicles are filtered at the view layer.

class VehicleListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year',
            'selling_price', 'discount', 'final_price', 'market_value',
            'fuel_type', 'transmission', 'mileage',
            'exterior_color', 'body_type',
            'status', 'cover_image', 'created_at',
        ]

    def get_cover_image(self, obj):
        cover = obj.images.filter(is_cover=True).first() or obj.images.first()
        if cover:
            request = self.context.get('request')
            return request.build_absolute_uri(cover.image.url) if request else cover.image.url
        return None


# ─── VEHICLE DETAIL — partner view (no sensitive data) ───────────────────────

class VehicleDetailSerializer(serializers.ModelSerializer):
    images      = VehicleImageSerializer(many=True, read_only=True)
    uploaded_by = UserSerializer(read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    # Masked identifiers for partners
    vin_masked          = serializers.CharField(read_only=True)
    engine_number_masked = serializers.CharField(read_only=True)
    documents   = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year',
            'selling_price', 'discount', 'final_price', 'market_value',
            'mileage', 'fuel_type', 'transmission',
            'engine_size', 'drive_type', 'body_type', 'seats',
            'exterior_color', 'interior_color', 'features',
            'vin_masked', 'engine_number_masked',
            'valuation_date', 'valuation_company',
            'description', 'status',
            'images', 'documents', 'uploaded_by',
            'created_at', 'updated_at',
        ]

    def get_documents(self, obj):
        # Partners only see approved documents
        qs = obj.documents.filter(is_partner_visible=True)
        return VehicleDocumentSerializer(qs, many=True, context=self.context).data


# ─── VEHICLE ADMIN DETAIL — full data for admin ───────────────────────────────

class VehicleAdminDetailSerializer(serializers.ModelSerializer):
    images      = VehicleImageSerializer(many=True, read_only=True)
    uploaded_by = UserSerializer(read_only=True)
    expenses    = VehicleExpenseSerializer(many=True, read_only=True)
    documents   = VehicleDocumentSerializer(many=True, read_only=True)

    # Calculated fields
    final_price     = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_expenses  = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_cost      = serializers.SerializerMethodField()
    expected_profit = serializers.SerializerMethodField()
    profit_margin   = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year',
            'vin', 'engine_number',
            'purchase_price', 'selling_price', 'discount', 'final_price', 'market_value',
            'total_expenses', 'total_cost', 'expected_profit', 'profit_margin',
            'mileage', 'fuel_type', 'transmission',
            'engine_size', 'drive_type', 'body_type', 'seats',
            'exterior_color', 'interior_color', 'features',
            'valuation_date', 'valuation_company',
            'description', 'status',
            'images', 'expenses', 'documents', 'uploaded_by',
            'created_at', 'updated_at',
        ]

    def get_total_cost(self, obj):
        return obj.total_cost

    def get_expected_profit(self, obj):
        return obj.expected_profit

    def get_profit_margin(self, obj):
        return obj.profit_margin


# ─── VEHICLE WRITE — create / edit ───────────────────────────────────────────

class VehicleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicle
        fields = [
            'id',
            'make', 'model', 'year',
            'vin', 'engine_number',
            'purchase_price', 'selling_price', 'discount', 'market_value',
            'mileage', 'fuel_type', 'transmission',
            'engine_size', 'drive_type', 'body_type', 'seats',
            'exterior_color', 'interior_color', 'features',
            'valuation_date', 'valuation_company',
            'description', 'status',
        ]
        read_only_fields = ['id']