from django.db import models
from django.contrib.auth.models import User
from apps.user_side.accounts.models import Address
from apps.admin_side.catalog.models import Product, ProductVariant, VariantCombination
import uuid


class Order(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('OUT_FOR_DELIVERY', 'Out For Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURNED', 'Returned'),
        ("RETURN_REJECTED", "Return Rejected"),
    ]

    PAYMENT_METHODS = [
        ('COD', 'Cash On Delivery'),
        ('RAZORPAY', 'Razorpay'),
        ('WALLET', 'Wallet'),
    ]

    order_id = models.CharField(max_length=30, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='COD')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    delivery_full_name = models.CharField(max_length=100, blank=True, default="")
    delivery_phone = models.CharField(max_length=15, blank=True, default="")
    delivery_house_no = models.CharField(max_length=255, blank=True, default="")
    delivery_city = models.CharField(max_length=100, blank=True, default="")
    delivery_state = models.CharField(max_length=100, blank=True, default="")
    delivery_pincode = models.CharField(max_length=10, blank=True, default="")

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_id


class OrderItem(models.Model):

    ITEM_STATUS = [
        ('ACTIVE', 'Active'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURNED', 'Returned'),
        ('RETURN_REJECTED', 'Return Rejected'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)


    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )


    combination = models.ForeignKey(
        VariantCombination,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    selected_options = models.JSONField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=ITEM_STATUS, default='ACTIVE')
    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)
    is_reviewed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.order.order_id} - {self.product.name}"


class OrderPayment(models.Model):
    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED",'refunded')
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)