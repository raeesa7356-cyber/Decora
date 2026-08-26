# urls.py


from django.urls import path
from . import views

urlpatterns = [
    path('', views.offer_list, name='offer_list'),
    path('create/', views.offer_create, name='offer_create'),
    path('edit/<str:offer_type>/<int:offer_id>/', views.offer_edit, name='offer_edit'),
    path('delete/<str:offer_type>/<int:offer_id>/', views.offer_delete, name='offer_delete'),
    path('referrals/', views.referral_offer_list, name='referral_offer_list'),
]

