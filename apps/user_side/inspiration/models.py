from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField

from apps.admin_side.catalog.models import (
    Product,
    Room,
    Category
)


class InspirationStyle(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class InspirationTag(models.Model):

    name = models.CharField(
        max_length=50,
        unique=True
    )

    def __str__(self):
        return self.name


class InspirationBoard(models.Model):

    title = models.CharField(max_length=200)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    cover_image = CloudinaryField(
        'inspiration_cover'
    )

    rooms = models.ManyToManyField(
        Room,
        related_name="inspirations",
        blank=True
    )

    categories = models.ManyToManyField(
        Category,
        related_name="inspirations",
        blank=True
    )

    products = models.ManyToManyField(
        Product,
        related_name="inspiration_boards",
        blank=True
    )

    style = models.ForeignKey(
        InspirationStyle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    tags = models.ManyToManyField(
        InspirationTag,
        blank=True
    )

    is_featured = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    priority = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["priority", "-created_at"]

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.title)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


from apps.admin_side.catalog.models import Product  # match whatever import path is actually correct in your project

class InspirationImage(models.Model):

    board = models.ForeignKey(
        InspirationBoard,
        related_name="gallery",
        on_delete=models.CASCADE
    )

    image = CloudinaryField('inspiration_gallery')

    product = models.ForeignKey(
        Product,
        related_name="inspiration_images",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    caption = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.board.title} Gallery"