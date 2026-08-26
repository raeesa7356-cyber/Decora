from django.urls import path
from . import views

urlpatterns = [

    path(
        "<int:order_id>/",
        views.order_detail,
        name="order_detail"
    ),

    path(
        "cancel-item/<int:item_id>/",
        views.cancel_item,
        name="cancel_item"
    ),

    path(
        "cancel-order/<int:order_id>/",
        views.cancel_order,
        name="cancel_order"
    ),

    path(
        "return-item/<int:item_id>/",
        views.return_item,
        name="return_item"
    ),

    path(
        "<int:order_id>/invoice/",
         views.download_invoice,
        name="download_invoice"
    ),

    path(
        "write-review/<int:item_id>/",
        views.write_review,
        name="write_review"
    ),
]