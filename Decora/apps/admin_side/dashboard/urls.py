from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login_view, name='admin-login'),
    path('dashboard/', views.admin_dashboard_view, name='admin-dashboard'),
    path('logout/', views.logout_view, name='logout-page'), # Admin specific logout
]