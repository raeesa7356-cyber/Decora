from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),  

    path('', include('apps.user_side.accounts.urls')), 
    path('accounts/', include('allauth.urls')),
    
    path('admin-panel/', include('apps.admin_side.dashboard.urls')),
    path("admin-panel/inspiration/", include("apps.admin_side.inspiration.urls")),
    path('admin-panel/customers/', include('apps.admin_side.customers.urls')),
    path('admin-panel/catalog/', include('apps.admin_side.catalog.urls')), 
    path(
    'admin-panel/orders/',
    include('apps.admin_side.orders.urls')
),
    path(
    "admin-panel/",
    include("apps.admin_side.sales.urls")
),
    path('django-admin/', admin.site.urls),
    path('shop/', include(('apps.user_side.shop.urls','shop'),namespace='shop')),
    path('cart/', include('apps.user_side.cart.urls')),
    path('checkout/', include('apps.user_side.checkout.urls')),
path('orders/', include('apps.user_side.orders.urls')),
    path('admin-panel/coupons/', include('apps.admin_side.coupons.urls')),
path('admin-panel/offers/', include('apps.admin_side.offers.urls')),
    path("inspiration/", include("apps.user_side.inspiration.urls")),
    path('contact/', include('apps.user_side.support.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)