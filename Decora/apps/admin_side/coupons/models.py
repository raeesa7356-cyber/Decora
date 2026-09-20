from django.db import models
from django.contrib.auth.models import User
from apps.admin_side.catalog.models import Product, Category
from apps.admin_side.orders.models import Order
from django.utils import timezone



class Coupon(models.Model):
    
    DISCOUNT_TYPE_CHOICES = (
        ('flat', 'Flat Amount'),
        ('percentage', 'Percentage'),
    )

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='flat')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True)
    total_usage_limit = models.PositiveIntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def total_used_count(self):
        return self.usages.count()
    
    @property
    def is_expired(self):
        return timezone.now() > self.valid_until
    
class CouponUsage(models.Model):
    
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(
    Order,
    on_delete=models.SET_NULL,blank=True,null=True)
    used_at = models.DateTimeField(auto_now_add=True
    )

    def __str__(self):
        return f"{self.coupon.code} - {self.user.username}"