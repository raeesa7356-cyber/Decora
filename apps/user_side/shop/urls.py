from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('home/', views.home_view, name='home'),
    path('product/', views.product_list, name='product-list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/buy-now/', views.buy_now, name='buy_now'),
    path('wishlist/',views.wishlist_view,name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/remove/<int:product_id>/',views.remove_from_wishlist,name='remove_from_wishlist'),
path('wishlist-status/<int:product_id>/<int:combination_id>/', views.combination_wishlist_status, name='combination_wishlist_status'),  
path('wishlist/add-to-cart/<int:product_id>/',views.add_wishlist_to_cart,name='add_wishlist_to_cart'),
]
