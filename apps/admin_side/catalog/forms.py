from django import forms
from .models import Category, Product, Room, ProductVariant, VariantCombination
from django.core.exceptions import ValidationError


class CategoryForm(forms.ModelForm):
    STATUS_CHOICES = [
        ('active', 'Active (Live)'),
        ('inactive', 'Inactive (Hidden)'),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect
    )

    class Meta:
        model = Category
        fields = ['name', 'description', 'cover_image']
        widgets = {
        'name': forms.TextInput(attrs={
            'class': 'w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-white focus:border-[#E3C565] outline-none transition',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-white focus:border-[#E3C565] outline-none transition',
                    'rows': 3,
                }),
                'cover_image': forms.FileInput(attrs={
                    'id': 'imageInput',
                    'class': 'absolute inset-0 opacity-0 cursor-pointer z-10',
                    'accept': 'image/*'
                }),
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['description'].required = True

        if self.instance and self.instance.pk:
            self.initial['status'] = 'active' if self.instance.is_active else 'inactive'
            self.fields['cover_image'].required = False if self.instance.cover_image else True
        else:
            self.fields['cover_image'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        queryset = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("This category name already exists.")
        return name


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'room', 'is_active', 'is_featured']
        widgets = {
        'name': forms.TextInput(attrs={'placeholder': 'Product Name', 'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50'}),
            'description': forms.Textarea(attrs={'placeholder': 'Detailed Description...', 'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white h-40 outline-none focus:border-[#D4AF37]/50', 'rows': 4}),
                'category': forms.Select(attrs={'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none text-xs'}),
                'room': forms.SelectMultiple(attrs={'class': 'select2-rooms w-full'}),
                'is_active': forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
                'is_featured': forms.CheckboxInput(attrs={'class': 'hidden peer'}),
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['room'].queryset = Room.objects.filter(is_active=True)
        self.fields['name'].required = True
        self.fields['category'].required = True
        self.fields['room'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        queryset = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("A product with this name already exists.")
        return name

    def clean(self):
        cleaned_data = super().clean()
     
        if self.instance and self.instance.pk:
            if not self.instance.has_complete_combination:
                raise ValidationError(
            "Activate all combinations for this product."
            "otherwise this product will move to archieve."
        )
        return cleaned_data


class VariantValueForm(forms.Form):
   
    VARIANT_TYPE_CHOICES = [
        ('', 'Select Type'),
        ('Color', 'Color'),
        ('Size', 'Size'),
        ('Material', 'Material'),
    ]

    variant_type = forms.ChoiceField(
        choices=VARIANT_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_variant_type',
            'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50 appearance-none cursor-pointer transition-all'
            })
        )
    values = forms.CharField(
            widget=forms.HiddenInput(attrs={'id': 'id_values_hidden'})
        )

    def clean_variant_type(self):
        variant_type = self.cleaned_data.get('variant_type')
        if not variant_type:
            raise ValidationError("Select a variant type.")
        return variant_type

    def clean_values(self):
        raw = self.cleaned_data.get('values', '')
        values = [v.strip() for v in raw.split(',') if v.strip()]
        if not values:
            raise ValidationError("Add at least one value.")

        seen = set()
        cleaned = []
        for v in values:
            key = v.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(v)
        return cleaned


class VariantForm(forms.ModelForm):
  
    class Meta:
        model = ProductVariant
        fields = ['variant_type', 'variant_value']
        widgets = {
        'variant_type': forms.Select(
            choices=[('', 'Select Type'), ('Material', 'Material'), ('Color', 'Color'), ('Size', 'Size')],
            attrs={'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50 appearance-none cursor-pointer transition-all'}
            ),
            'variant_value': forms.TextInput(attrs={'placeholder': 'e.g. Ceramic', 'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50 transition-all'}),
            }


class VariantCombinationForm(forms.ModelForm):
    variants = forms.ModelMultipleChoiceField(
        queryset=ProductVariant.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Attribute values in this combination"
    )

    class Meta:
        model = VariantCombination
        fields = ['variants', 'original_price', 'discount_price', 'stock_quantity', 'sku', 'main_image', 'is_default']
        widgets = {
        'original_price': forms.NumberInput(attrs={'placeholder': '0.00', 'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50'}),
            'discount_price': forms.NumberInput(attrs={'placeholder': '0.00', 'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50'}),
                'stock_quantity': forms.NumberInput(attrs={'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white outline-none focus:border-[#D4AF37]/50'}),
                    'sku': forms.TextInput(attrs={'class': 'w-full bg-black/40 border border-white/10 rounded-xl p-4 text-[#D4AF37] font-mono outline-none'}),
                        'main_image': forms.FileInput(attrs={
                            'id': 'id_main_image',
                            'class': 'absolute inset-0 opacity-0 cursor-pointer z-10',
                            'accept': 'image/*'
                        }),
                    }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product or (self.instance.product if self.instance and self.instance.pk else None)
        if self.product:
            self.fields['variants'].queryset = self.product.variants.filter(is_active=True)

            # main_image required unless we already have one saved
        self.fields['main_image'].required = not bool(
                self.instance and self.instance.pk and self.instance.main_image
            )

    def clean(self):
        cleaned_data = super().clean()
        original = cleaned_data.get('original_price')
        discount = cleaned_data.get('discount_price')
        if discount is not None and original is not None and discount >= original:
            self.add_error('discount_price', "Discount price must be less than original price.")
        return cleaned_data

    def clean_variants(self):
        variants = self.cleaned_data.get('variants')
        if not variants:
            raise ValidationError("Select at least one attribute value.")

        seen_types = set()
        for v in variants:
            if v.variant_type in seen_types:
                raise ValidationError(
            f"You picked two values for '{v.variant_type}'. Choose only one value per attribute type."
        )
            seen_types.add(v.variant_type)

        variant_ids = set(v.id for v in variants)
        existing = VariantCombination.objects.filter(product=self.product)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        for combo in existing:
            if set(combo.variants.values_list('id', flat=True)) == variant_ids:
                raise ValidationError("This exact combination already exists.")

        return variants


class RoomForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[
            ('active', 'Active (Visible)'),
            ('inactive', 'Inactive (Hidden)')
        ],
        widget=forms.RadioSelect(attrs={'class': 'w-4 h-4 accent-[#E3C565]'}),
            initial='active'
        )

    class Meta:
        model = Room
        fields = ['name']
        widgets = {
        'name': forms.TextInput(attrs={
            'placeholder': 'e.g., Living Room, Minimalist Study',
            'class': 'w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-white placeholder:text-gray-700 focus:border-[#E3C565] outline-none transition',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['status'] = 'active' if self.instance.is_active else 'inactive'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_active = (self.cleaned_data.get('status') == 'active')
        if commit:
            instance.save()
        return instance