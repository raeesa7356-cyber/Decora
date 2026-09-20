from django.urls import path

from . import views

urlpatterns = [
    path(
        '',
        views.checkout,
        name='checkout'
    ),

    path(
        'success/<int:order_id>/',
        views.order_success,
        name='order_success'
    ),

    path(
        'set-default-address/',
        views.set_default_address,
        name='checkout_set_default_address'
    ),
    path(
    'payment/<int:order_id>/',
    views.checkout_payment,
    name='checkout_payment'
),

    path(
    'verify-payment/',
    views.verify_order_payment,
    name='verify_order_payment'
),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
path('order/<int:order_id>/payment-failed/', views.order_payment_failed, name='order_payment_failed'),
path('order/<int:order_id>/retry-payment/', views.retry_payment, name='retry_payment'),
]