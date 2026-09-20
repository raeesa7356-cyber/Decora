from django import forms

from apps.user_side.inspiration.models import (
    InspirationBoard,InspirationImage,
    InspirationStyle,InspirationTag
)

from apps.admin_side.catalog.models import (
    Product,
    Room,
    Category
)

class InspirationForm(forms.ModelForm):

    class Meta:

        model = InspirationBoard

        fields = [
        "title","description",
        "cover_image","rooms",
        "categories","products",
        "style","tags",
        "is_featured","is_active",
        "priority"
        ]

        widgets = {
        "title": forms.TextInput(
            attrs={
                "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10 focus:border-[#D4AF37] outline-none",
                    "placeholder": "Inspiration Title"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10 focus:border-[#D4AF37] outline-none",
                        "placeholder": "Write inspiration story...",
                        "rows": 5
                    }
                ),

            "rooms": forms.SelectMultiple(
                    attrs={
                        "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10"
                    }
                ),

            "categories": forms.SelectMultiple(
                    attrs={
                        "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10"
                    }
                ),

            "products": forms.SelectMultiple(
                    attrs={
                        "id": "products-select",
                        "class": "w-full"
                    }
                ),

            "style": forms.Select(
                    attrs={
                        "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10 focus:border-[#D4AF37] outline-none"
                    }
                ),

            "tags": forms.SelectMultiple(
                attrs={
                    "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10"
                }
            ),

            "priority": forms.NumberInput(
                attrs={
                    "class": "w-full p-4 bg-black text-white rounded-2xl border border-white/10",
                    "placeholder": "Priority"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].required = True
        self.fields["cover_image"].required = False

        self.fields["products"].queryset = (
            Product.objects.filter(
                is_active=True,
                is_archived=False
            )
        )
        self.fields["rooms"].queryset = (
            Room.objects.filter(
                is_active=True
            )
        )
        self.fields["categories"].queryset = (
            Category.objects.filter(
                is_active=True
            )
        )
        self.fields["is_featured"].widget.attrs.update({
            "class": "w-5 h-5 accent-[#D4AF37]"
            })
        self.fields["is_active"].widget.attrs.update({
                "class": "w-5 h-5 accent-[#D4AF37]"
                })

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if len(title.strip()) < 3:
            raise forms.ValidationError(
        "Title must contain at least 3 characters."
            )
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            if len(description.strip()) < 10:
                raise forms.ValidationError(
            "Description must contain at least 10 characters."
                )
        return description


class InspirationGalleryForm(forms.ModelForm):
    class Meta:
        model = InspirationImage
        fields = [
        "image","caption"
        ]
        
        widgets = {
        "caption": forms.TextInput(
            attrs={
                "class": "w-full p-3 bg-black text-white rounded-xl border border-white/10",
                "placeholder": "Image Caption"
            }
        )
    }


class StyleForm(forms.ModelForm):
    class Meta:
        model = InspirationStyle
        fields = [
        "name","is_active"
        ]
        widgets = {
        "name": forms.TextInput(
            attrs={
                "class": "w-full p-3 bg-black text-white rounded-xl border border-white/10 focus:border-[#D4AF37] outline-none",
                    "placeholder": "Style name"
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].widget.attrs.update({
            "class": "w-5 h-5 accent-[#D4AF37]"
            })

class TagForm(forms.ModelForm):
    class Meta:
        model = InspirationTag
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({
            "class": "w-full p-3 bg-black text-white rounded-xl border border-white/10 focus:border-[#D4AF37] outline-none",
                "placeholder": "Enter tag name"
            })