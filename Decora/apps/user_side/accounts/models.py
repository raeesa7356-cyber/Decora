import os
from cloudinary.models import CloudinaryField
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from apps.core.utils import get_ui_avatar

class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.email}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    profile_image = CloudinaryField('image', null=True, blank=True) 

    @property
    def get_avatar(self):
        if self.profile_image:
            return self.profile_image.url
        
        name = self.user.first_name or self.user.username
        return get_ui_avatar(name)
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField(max_length=50, default="Home")
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    house_no = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_type} - {self.user.username}"

from django.db import models
from django.contrib.auth.models import User


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet'
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Wallet"


class WalletTransaction(models.Model):

    TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    PURPOSE_CHOICES = [
        ('wallet_recharge', 'Wallet Recharge'),
        ('order_payment', 'Order Payment'),
        ('return_refund', 'Return Refund'),
        ('cancellation_refund', 'Cancellation Refund'),
        ('referral_bonus', 'Referral Bonus'),
        ('cashback', 'Cashback'),
        ('admin_credit', 'Admin Credit'),
        ('admin_debit', 'Admin Debit'),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    purpose = models.CharField(
        max_length=50,
        choices=PURPOSE_CHOICES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.wallet.user.username} - {self.amount}"    
class WalletRecharge(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_signature = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount}"    