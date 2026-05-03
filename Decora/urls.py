from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('accounts.urls')), 
    path('accounts/', include('allauth.urls')),
    path('admin-panel/', include('admin.urls')),
]