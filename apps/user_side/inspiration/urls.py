from django.urls import path
from . import views
app_name="user_inspiration"
urlpatterns = [
    path("", views.inspiration_list, name="list"),
    path("<int:pk>/", views.inspiration_detail, name="detail"),
  
    path("gallery/<int:id>/set-product/", views.gallery_set_product, name="gallery_set_product"),
]