from django import forms

class UserFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('blocked', 'Blocked'),
    ]
    SORT_CHOICES = [
        ('', 'Default'),
        ('new', 'Newest First'),
        ('old', 'Oldest First'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search name or email...',
            'class': 'bg-transparent border-none text-sm outline-none w-full text-gray-300 placeholder-gray-600'
        })
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.HiddenInput()  # We'll use custom buttons, but keep the value in a hidden field
    )
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.HiddenInput()
    )