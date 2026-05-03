from django.urls import path
from . import views

urlpatterns = [
    # ... your other urls
    
    path('login/', views.admin_login_view, name='admin-login'),
    path('dashboard/', views.admin_dashboard_view, name='admin-dashboard'),
path('users/', views.user_management_view, name='user-management'),
path('logout/',views.logout_view,name='logout-page'),
path('users/<int:user_id>/', views.user_detail_view, name='user-detail'),
path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle-user-status'),
]