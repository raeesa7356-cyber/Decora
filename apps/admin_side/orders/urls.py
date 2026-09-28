from django.urls import path
from . import views

urlpatterns = [
    path('',views.order_list,name='admin_order_list'),
    path('<int:order_id>/',views.order_detail,name='admin_order_detail'),
    path('inventory/',views.inventory_list,name='inventory_list'),
    path('inventory/update/<int:combination_id>/',   views.update_stock,name='update_stock'),
    path('inventory/<int:product_id>/',views.inventory_detail,name='inventory_detail'),
    path("returns/",views.return_requests,name="admin_return_requests"),
    path("reviews/<int:review_id>/unhide/",views.unhide_review,name="unhide_review"),
    path("returns/<int:item_id>/approve/",views.approve_return,name="approve_return"),
    path("returns/<int:item_id>/reject/",views.reject_return,name="reject_return"),
    path("returns/<int:item_id>/",views.return_request_detail,name="return_request_detail"),
    path("reviews/", views.review_list, name="admin_reviews"),
    path("reviews/<int:review_id>/", views.review_detail, name="admin_review_detail"),
    path("reviews/<int:review_id>/approve/", views.approve_review, name="approve_review"),
    path("reviews/<int:review_id>/hide/", views.hide_review, name="hide_review"),
    path("reviews/<int:review_id>/delete/", views.delete_review, name="delete_review"),
]
