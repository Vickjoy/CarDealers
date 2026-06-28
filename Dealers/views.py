from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import models
from .models import User, Vehicle, VehicleImage, VehicleExpense, VehicleDocument
from .permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from .serializers import (
    LoginSerializer, UserSerializer, CreateUserSerializer,
    VehicleListSerializer, VehicleDetailSerializer, VehicleAdminDetailSerializer,
    VehicleWriteSerializer, VehicleImageSerializer,
    VehicleExpenseSerializer, VehicleDocumentSerializer,
)


# ─── HELPER ──────────────────────────────────────────────────────────────────

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(
        request,
        username=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
    )
    if user is None:
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'user': UserSerializer(user).data, 'tokens': get_tokens_for_user(user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        RefreshToken(refresh_token).blacklist()
        return Response({'message': 'Logged out successfully'})
    except TokenError:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        return Response({'access': str(token.access_token)})
    except TokenError:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


# ─── VEHICLE LIST & CREATE ────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehicle_list_create(request):
    is_admin = IsAdminOrSuperAdmin().has_permission(request, None)

    if request.method == 'GET':
        vehicles = Vehicle.objects.prefetch_related('images').all()

        # Partners never see drafts
        if not is_admin:
            vehicles = vehicles.exclude(status='draft')

        # Search
        search = request.query_params.get('search')
        if search:
            vehicles = vehicles.filter(
                models.Q(make__icontains=search) | models.Q(model__icontains=search)
            )

        # Filters
        for param, field in [
            ('status',       'status'),
            ('fuel_type',    'fuel_type'),
            ('transmission', 'transmission'),
            ('body_type',    'body_type'),
        ]:
            val = request.query_params.get(param)
            if val:
                vehicles = vehicles.filter(**{field: val})

        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            vehicles = vehicles.filter(selling_price__gte=min_price)
        if max_price:
            vehicles = vehicles.filter(selling_price__lte=max_price)

        serializer = VehicleListSerializer(vehicles, many=True, context={'request': request})
        return Response(serializer.data)

    # POST — admin only
    if not is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = VehicleWriteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── VEHICLE DETAIL, UPDATE, DELETE ──────────────────────────────────────────

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def vehicle_detail(request, pk):
    is_admin = IsAdminOrSuperAdmin().has_permission(request, None)

    try:
        vehicle = Vehicle.objects.prefetch_related('images', 'expenses', 'documents').get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    # Partners cannot view drafts
    if vehicle.status == 'draft' and not is_admin:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Admins get full data including financials; partners get sanitised view
        if is_admin:
            serializer = VehicleAdminDetailSerializer(vehicle, context={'request': request})
        else:
            serializer = VehicleDetailSerializer(vehicle, context={'request': request})
        return Response(serializer.data)

    if not is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method in ['PUT', 'PATCH']:
        partial    = request.method == 'PATCH'
        serializer = VehicleWriteSerializer(vehicle, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        vehicle.delete()
        return Response({'message': 'Vehicle deleted'}, status=status.HTTP_204_NO_CONTENT)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vehicle_publish(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
 
    try:
        vehicle = Vehicle.objects.prefetch_related('images', 'expenses').get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
 
    if vehicle.status != 'draft':
        return Response(
            {'error': f'Vehicle is already published (status: {vehicle.status})'},
            status=status.HTTP_400_BAD_REQUEST,
        )
 
    # ── Readiness checks ──────────────────────────────────────────────────────
    errors = []
 
    if not vehicle.selling_price:
        errors.append('Selling price is required before publishing')
 
    if not vehicle.images.exists():
        errors.append('At least one image is required before publishing')
 
    if not vehicle.description or not vehicle.description.strip():
        errors.append('A description is required before publishing')
 
    if errors:
        return Response(
            {'error': 'Vehicle is not ready to publish', 'details': errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # ─────────────────────────────────────────────────────────────────────────
 
    vehicle.status = 'available'
    vehicle.save()
    return Response({'message': 'Vehicle published successfully', 'status': 'available'})

    
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
    valid = ['draft', 'available', 'reserved', 'sold']
    if new_status not in valid:
        return Response(
            {'error': f'Status must be one of: {valid}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    vehicle.status = new_status
    vehicle.save()
    return Response({'message': f'Status updated to {new_status}'})


# ─── VEHICLE IMAGES ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vehicle_image_upload(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    images = request.FILES.getlist('images')
    if not images:
        return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)

    existing_count = vehicle.images.count()
    created = []
    for index, image_file in enumerate(images):
        is_cover = (existing_count == 0 and index == 0)
        img = VehicleImage.objects.create(
            vehicle=vehicle, image=image_file,
            is_cover=is_cover, order=existing_count + index,
        )
        created.append(VehicleImageSerializer(img, context={'request': request}).data)

    return Response(created, status=status.HTTP_201_CREATED)


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

    if was_cover:
        next_image = vehicle.images.first()
        if next_image:
            next_image.is_cover = True
            next_image.save()

    return Response({'message': 'Image deleted'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def vehicle_image_set_cover(request, image_id):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        image = VehicleImage.objects.get(pk=image_id)
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    image.vehicle.images.update(is_cover=False)
    image.is_cover = True
    image.save()
    return Response({'message': 'Cover image updated'})


# ─── VEHICLE EXPENSES (admin only) ───────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehicle_expense_list_create(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        expenses   = vehicle.expenses.all()
        serializer = VehicleExpenseSerializer(expenses, many=True)
        total      = vehicle.total_expenses
        return Response({'expenses': serializer.data, 'total': total})

    serializer = VehicleExpenseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(vehicle=vehicle)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def vehicle_expense_detail(request, pk, expense_id):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        expense = VehicleExpense.objects.get(pk=expense_id, vehicle_id=pk)
    except VehicleExpense.DoesNotExist:
        return Response({'error': 'Expense not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        expense.delete()
        return Response({'message': 'Expense deleted'}, status=status.HTTP_204_NO_CONTENT)

    partial    = request.method == 'PATCH'
    serializer = VehicleExpenseSerializer(expense, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── VEHICLE DOCUMENTS (admin manages; partners view approved) ────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehicle_document_list_create(request, pk):
    is_admin = IsAdminOrSuperAdmin().has_permission(request, None)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = vehicle.documents.all() if is_admin else vehicle.documents.filter(is_partner_visible=True)
        return Response(VehicleDocumentSerializer(qs, many=True, context={'request': request}).data)

    if not is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = VehicleDocumentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(vehicle=vehicle)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def vehicle_document_detail(request, pk, doc_id):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        doc = VehicleDocument.objects.get(pk=doc_id, vehicle_id=pk)
    except VehicleDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        doc.delete()
        return Response({'message': 'Document deleted'}, status=status.HTTP_204_NO_CONTENT)

    serializer = VehicleDocumentSerializer(doc, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── USER MANAGEMENT ──────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_list_create(request):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        users = User.objects.all().order_by('role', 'first_name')
        return Response(UserSerializer(users, many=True).data)

    if not IsSuperAdmin().has_permission(request, None):
        return Response({'error': 'Super admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = CreateUserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, pk):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(UserSerializer(user).data)

    if not IsSuperAdmin().has_permission(request, None):
        return Response({'error': 'Super admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if user == request.user:
        return Response(
            {'error': 'You cannot modify your own account from here'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == 'PATCH':
        serializer = CreateUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        user.delete()
        return Response({'message': 'User deleted'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_toggle_active(request, pk):
    if not IsSuperAdmin().has_permission(request, None):
        return Response({'error': 'Super admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if user == request.user:
        return Response({'error': 'You cannot deactivate your own account'}, status=status.HTTP_400_BAD_REQUEST)

    user.is_active = not user.is_active
    user.save()
    state = 'activated' if user.is_active else 'deactivated'
    return Response({'message': f'User {state} successfully', 'is_active': user.is_active})


# ─── DASHBOARD STATS ──────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    if not IsAdminOrSuperAdmin().has_permission(request, None):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    # Count by status
    counts = {
        'draft':     Vehicle.objects.filter(status='draft').count(),
        'available': Vehicle.objects.filter(status='available').count(),
        'reserved':  Vehicle.objects.filter(status='reserved').count(),
        'sold':      Vehicle.objects.filter(status='sold').count(),
    }
    counts['total'] = sum(counts.values())

    # Total potential profit across published vehicles with complete pricing
    from django.db.models import Sum, F, ExpressionWrapper, DecimalField
    published = Vehicle.objects.filter(status__in=['available', 'reserved'])

    # Aggregate expected profit dynamically
    total_profit = 0
    for v in published.prefetch_related('expenses'):
        if v.expected_profit is not None:
            total_profit += float(v.expected_profit)

    # Recent uploads (last 5, any status for admin)
    recent      = Vehicle.objects.prefetch_related('images').order_by('-created_at')[:5]
    recent_data = VehicleListSerializer(recent, many=True, context={'request': request}).data

    # Draft vehicles awaiting publication
    drafts      = Vehicle.objects.prefetch_related('images').filter(status='draft').order_by('-created_at')[:10]
    drafts_data = VehicleListSerializer(drafts, many=True, context={'request': request}).data

    return Response({
        'stats': {**counts, 'total_potential_profit': round(total_profit, 2)},
        'recent_uploads': recent_data,
        'drafts': drafts_data,
    })