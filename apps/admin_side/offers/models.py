from django.db import models
from django.contrib.auth.models import User
from apps.admin_side.catalog.models import Product, Category
import uuid


class ProductOffer(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    name = models.CharField(max_length=150, default='')
    description = models.TextField(blank=True, default='')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    discount_percent = models.DecimalField(max_digits=10, decimal_places=2)  
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or self.product.name}"


class CategoryOffer(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    name = models.CharField(max_length=150, default='')
    description = models.TextField(blank=True, default='')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='offers')
    discount_percent = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or self.category.name}"

def generate_token():
    return uuid.uuid4().hex



class ReferralOffer(models.Model):
    referrer = models.ForeignKey(User, related_name='referrals_made', on_delete=models.CASCADE)
    referred_user = models.ForeignKey(User, related_name='referred_by', on_delete=models.CASCADE, null=True, blank=True)
    referral_code = models.CharField(max_length=20, unique=True)
    token = models.CharField(max_length=64, unique=True, default=generate_token)  
    
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} -> {self.referral_code}"