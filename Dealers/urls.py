from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/login/',   views.login_view,   name='login'),
    path('auth/logout/',  views.logout_view,  name='logout'),
    path('auth/refresh/', views.refresh_view, name='refresh'),
    path('auth/me/',      views.me_view,      name='me'),

    # Vehicles
    path('vehicles/',                                 views.vehicle_list_create,    name='vehicle-list-create'),
    path('vehicles/<int:pk>/',                        views.vehicle_detail,         name='vehicle-detail'),
    path('vehicles/<int:pk>/status/',                 views.vehicle_status_update,  name='vehicle-status'),
    path('vehicles/<int:pk>/images/',                 views.vehicle_image_upload,   name='vehicle-image-upload'),
    path('vehicles/images/<int:image_id>/',           views.vehicle_image_delete,   name='vehicle-image-delete'),
    path('vehicles/images/<int:image_id>/cover/',     views.vehicle_image_set_cover, name='vehicle-image-cover'),

    # Users
    path('users/',                   views.user_list_create,  name='user-list-create'),
    path('users/<int:pk>/',          views.user_detail,       name='user-detail'),
    path('users/<int:pk>/toggle/',   views.user_toggle_active, name='user-toggle'),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
]