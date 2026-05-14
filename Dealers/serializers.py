from rest_framework import serializers
from .models import User, Vehicle, VehicleImage


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


# ─── VEHICLE LIST (compact — for browsing) ───────────────────────────────────

class VehicleListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'price',
            'fuel_type', 'transmission', 'mileage',
            'status', 'cover_image', 'created_at'
        ]

    def get_cover_image(self, obj):
        cover = obj.images.filter(is_cover=True).first()
        if not cover:
            cover = obj.images.first()
        if cover:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(cover.image.url)
            return cover.image.url
        return None


# ─── VEHICLE DETAIL (full — for single vehicle page) ─────────────────────────

class VehicleDetailSerializer(serializers.ModelSerializer):
    images      = VehicleImageSerializer(many=True, read_only=True)
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'price',
            'mileage', 'fuel_type', 'transmission',
            'color', 'engine_size', 'description',
            'status', 'images', 'uploaded_by',
            'created_at', 'updated_at'
        ]


# ─── VEHICLE WRITE (for create & edit) ───────────────────────────────────────

class VehicleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicle
        fields = [
            'make', 'model', 'year', 'price',
            'mileage', 'fuel_type', 'transmission',
            'color', 'engine_size', 'description', 'status'
        ]