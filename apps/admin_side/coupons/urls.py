from django.urls import path
from . import views

urlpatterns = [
    path('', views.coupon_list, name='coupon_list'),
    path('create/', views.coupon_create, name='coupon_create'),
    path('edit/<int:coupon_id>/', views.coupon_edit, name='coupon_edit'),
    path('delete/<int:coupon_id>/', views.coupon_delete, name='coupon_delete'),
    path('toggle-active/<int:coupon_id>/', views.coupon_toggle_active, name='coupon_toggle_active'),
    path('generate-code/', views.coupon_generate_code, name='coupon_generate_code'),
]