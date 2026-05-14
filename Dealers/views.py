from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import models
from .models import User, Vehicle, VehicleImage
from .serializers import (
    LoginSerializer, UserSerializer,
    VehicleListSerializer, VehicleDetailSerializer,
    VehicleWriteSerializer, VehicleImageSerializer
)

from .permissions import IsAdminOrSuperAdmin


# ─── HELPER ──────────────────────────────────────────────────────────────────

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


# ─── LOGIN ───────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email    = serializer.validated_data['email']
    password = serializer.validated_data['password']
    user     = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'Account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )

    tokens = get_tokens_for_user(user)

    return Response({
        'user':   UserSerializer(user).data,
        'tokens': tokens,
    }, status=status.HTTP_200_OK)


# ─── LOGOUT ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response(
            {'error': 'Refresh token required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


# ─── REFRESH ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response(
            {'error': 'Refresh token required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token  = RefreshToken(refresh_token)
        return Response({
            'access': str(token.access_token)
        }, status=status.HTTP_200_OK)
    except TokenError:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)


# ─── ME ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

# ─── VEHICLE LIST & CREATE ────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
def vehicle_list_create(request):

    # GET — all authenticated users can browse
    if request.method == 'GET':
        vehicles = Vehicle.objects.prefetch_related('images').all()

        # Search
        search = request.query_params.get('search')
        if search:
            vehicles = vehicles.filter(
                models.Q(make__icontains=search) |
                models.Q(model__icontains=search)
            )

        # Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            vehicles = vehicles.filter(status=status_filter)

        fuel_filter = request.query_params.get('fuel_type')
        if fuel_filter:
            vehicles = vehicles.filter(fuel_type=fuel_filter)

        transmission_filter = request.query_params.get('transmission')
        if transmission_filter:
            vehicles = vehicles.filter(transmission=transmission_filter)

        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            vehicles = vehicles.filter(price__gte=min_price)
        if max_price:
            vehicles = vehicles.filter(price__lte=max_price)

        serializer = VehicleListSerializer(vehicles, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — admin only
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = VehicleWriteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── VEHICLE DETAIL, UPDATE, DELETE ──────────────────────────────────────────

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def vehicle_detail(request, pk):
    try:
        vehicle = Vehicle.objects.prefetch_related('images').get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    # GET — all authenticated users
    if request.method == 'GET':
        serializer = VehicleDetailSerializer(vehicle, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT/PATCH/DELETE — admin only
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method in ['PUT', 'PATCH']:
        partial    = request.method == 'PATCH'
        serializer = VehicleWriteSerializer(vehicle, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        vehicle.delete()
        return Response({'message': 'Vehicle deleted'}, status=status.HTTP_204_NO_CONTENT)


# ─── UPDATE VEHICLE STATUS ────────────────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def vehicle_status_update(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    valid = ['available', 'reserved', 'sold']

    if new_status not in valid:
        return Response(
            {'error': f'Status must be one of: {valid}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    vehicle.status = new_status
    vehicle.save()
    return Response({'message': f'Status updated to {new_status}'}, status=status.HTTP_200_OK)


# ─── UPLOAD IMAGES ────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vehicle_image_upload(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    images  = request.FILES.getlist('images')
    if not images:
        return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)

    # If vehicle has no images yet, first uploaded becomes cover
    existing_count = vehicle.images.count()
    created = []

    for index, image_file in enumerate(images):
        is_cover = (existing_count == 0 and index == 0)
        img = VehicleImage.objects.create(
            vehicle  = vehicle,
            image    = image_file,
            is_cover = is_cover,
            order    = existing_count + index
        )
        created.append(VehicleImageSerializer(img, context={'request': request}).data)

    return Response(created, status=status.HTTP_201_CREATED)


# ─── DELETE IMAGE ─────────────────────────────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vehicle_image_delete(request, image_id):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        image = VehicleImage.objects.get(pk=image_id)
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    was_cover = image.is_cover
    vehicle   = image.vehicle
    image.delete()

    # If deleted image was the cover, assign cover to next available image
    if was_cover:
        next_image = vehicle.images.first()
        if next_image:
            next_image.is_cover = True
            next_image.save()

    return Response({'message': 'Image deleted'}, status=status.HTTP_204_NO_CONTENT)


# ─── SET COVER IMAGE ──────────────────────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def vehicle_image_set_cover(request, image_id):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        image = VehicleImage.objects.get(pk=image_id)
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    # Remove cover from all images of this vehicle first
    image.vehicle.images.update(is_cover=False)

    # Set this one as cover
    image.is_cover = True
    image.save()

    return Response({'message': 'Cover image updated'}, status=status.HTTP_200_OK)