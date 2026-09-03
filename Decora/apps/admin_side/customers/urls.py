from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_management_view, name='user-management'),
    path('users/<int:user_id>/', views.user_detail_view, name='user-detail'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle-user-status'),
]