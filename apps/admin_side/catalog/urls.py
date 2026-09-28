from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('management/', views.category_room_list, name='category-list'),

    path('category/add/', views.add_category, name='category-add'),
    path('category/edit/<int:pk>/', views.edit_category, name='category-edit'),
    path('category/restore/<int:pk>/', views.restore_category, name='category-restore'),

    path('room/add/', views.add_room, name='room-add'),
    path('room/edit/<int:pk>/', views.edit_room, name='room-edit'),

    path('products/', views.admin_product_list, name='admin-product-list'),
    path('products/add/', views.admin_product_upsert, name='admin-product-add'),
    path('products/edit/<int:pk>/', views.admin_product_upsert, name='admin-product-edit'),
    path('products/delete/<int:pk>/', views.admin_product_delete, name='admin_product_delete'),
    path('products/archives/', views.admin_product_archives, name='admin_product_archives'),
    path('products/restore/<int:pk>/', views.admin_product_restore, name='admin_product_restore'),

    path('products/<int:product_id>/variants/', views.admin_manage_variants, name='admin-manage-variants'),
    path('products/<int:product_id>/variants/add/', views.admin_add_variant, name='add_variant'),
    path('variants/edit/<int:pk>/', views.admin_edit_variant, name='admin-edit-variant'),
    path('variants/<int:pk>/toggle-status/', views.toggle_variant_status, name='toggle_variant_status'),

    path('products/<int:product_id>/combinations/add/', views.admin_add_combination, name='add_combination'),
    path('products/<int:product_id>/combinations/edit/<int:pk>/',views.admin_add_combination,name='admin-edit-combination')   ,
    path('combinations/<int:pk>/toggle-status/', views.toggle_combination_status, name='toggle_combination_status'),
    path('products/<int:product_id>/variants/generate/', views.admin_generate_combinations, name='generate_combinations'),
]