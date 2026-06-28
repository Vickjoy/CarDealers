from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('auth/login/',   views.login_view,   name='login'),
    path('auth/logout/',  views.logout_view,  name='logout'),
    path('auth/refresh/', views.refresh_view, name='refresh'),
    path('auth/me/',      views.me_view,      name='me'),

    # ── Vehicles ──────────────────────────────────────────────────────────────
    path('vehicles/',                         views.vehicle_list_create,    name='vehicle-list-create'),
    path('vehicles/<int:pk>/',                views.vehicle_detail,         name='vehicle-detail'),
    path('vehicles/<int:pk>/publish/',        views.vehicle_publish,        name='vehicle-publish'),
    path('vehicles/<int:pk>/status/',         views.vehicle_status_update,  name='vehicle-status'),

    # ── Vehicle images ────────────────────────────────────────────────────────
    path('vehicles/<int:pk>/images/',                   views.vehicle_image_upload,    name='vehicle-image-upload'),
    path('vehicles/images/<int:image_id>/',             views.vehicle_image_delete,    name='vehicle-image-delete'),
    path('vehicles/images/<int:image_id>/cover/',       views.vehicle_image_set_cover, name='vehicle-image-cover'),

    # ── Vehicle expenses (admin) ───────────────────────────────────────────────
    path('vehicles/<int:pk>/expenses/',                 views.vehicle_expense_list_create, name='vehicle-expense-list'),
    path('vehicles/<int:pk>/expenses/<int:expense_id>/', views.vehicle_expense_detail,     name='vehicle-expense-detail'),

    # ── Vehicle documents ─────────────────────────────────────────────────────
    path('vehicles/<int:pk>/documents/',                views.vehicle_document_list_create, name='vehicle-doc-list'),
    path('vehicles/<int:pk>/documents/<int:doc_id>/',   views.vehicle_document_detail,      name='vehicle-doc-detail'),

    # ── Users ─────────────────────────────────────────────────────────────────
    path('users/',               views.user_list_create,  name='user-list-create'),
    path('users/<int:pk>/',      views.user_detail,       name='user-detail'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user-toggle-active'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard_stats, name='dashboard'),
]