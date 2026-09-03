from django.db import models
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    cover_image = CloudinaryField('image', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    room = models.ManyToManyField('Room', related_name='products')
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def selected_rooms(self):
        return ", ".join(self.room.values_list("name", flat=True))

    @property
    def starting_price(self):
        active_combos = self.combinations.filter(is_active=True)
        if not active_combos.exists():
            return None
        return min(c.selling_price for c in active_combos)

    @property
    def default_combination(self):
        return (
    self.combinations.filter(is_active=True, is_default=True).first()
    or self.combinations.filter(is_active=True).order_by('id').first()
)

    @property
    def has_complete_combination(self):
        active = self.combinations.filter(is_active=True)
        return any(c.has_min_images for c in active)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    variant_name = models.CharField(max_length=100, blank=True)
    variant_type = models.CharField(max_length=50)
    variant_value = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    # TEMPORARY — still has real data in the DB. Do not remove yet.
    variant_image = CloudinaryField('variant_image', null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ('product', 'variant_type', 'variant_value')

    def save(self, *args, **kwargs):
        self.variant_name = f"{self.variant_type}: {self.variant_value}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.variant_value}"


class ProductGallery(models.Model):
    
    variant = models.ForeignKey(ProductVariant, related_name='gallery', on_delete=models.CASCADE)
    image = CloudinaryField('gallery_image')

    def __str__(self):
        return f"Gallery Image for {self.variant.variant_name}"


class VariantCombination(models.Model):
    product = models.ForeignKey(Product, related_name='combinations', on_delete=models.CASCADE)
    variants = models.ManyToManyField(ProductVariant, related_name='combinations')

    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # NEW — replaces the old single 'cover_image'
    main_image = CloudinaryField('combination_main_image', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def selling_price(self):
        if self.discount_price is not None and self.discount_price < self.original_price:
            return self.discount_price
        return self.original_price

    @property
    def is_out_of_stock(self):
        return self.stock_quantity <= 0

    @property
    def label(self):
        return " / ".join(self.variants.values_list('variant_value', flat=True))

    @property
    def display_image(self):
        return self.main_image

    @property
    def has_min_images(self):
        return bool(self.main_image) and self.gallery.count() >= 3

    def clean(self):
        if self.discount_price is not None and self.discount_price >= self.original_price:
            raise ValidationError("Discount price must be less than original price.")

    def __str__(self):
        return f"{self.product.name} - {self.label}"


class CombinationGallery(models.Model):
    
    combination = models.ForeignKey(VariantCombination, related_name='gallery', on_delete=models.CASCADE)
    image = CloudinaryField('combination_gallery_image')

    def __str__(self):
        return f"Gallery Image for {self.combination.label}"