from django.db import models
from django.contrib.auth.models import User # This is the one we want to use

class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.email}"

class Profile(models.Model):
    objects = models.Manager() 
    # Link to the built-in Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Move your custom fields here!
    phone = models.CharField(max_length=15, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
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