from django.db import models
from django.contrib.auth.models import User
from apps.admin_side.catalog.models import Product, VariantCombination


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)


    combination = models.ForeignKey(VariantCombination, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'combination'],
                name='unique_user_combination_cart'
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.product.name} - {self.combination.label}"