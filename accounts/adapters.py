from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.contrib import messages
from allauth.core.exceptions import ImmediateHttpResponse # Add this import

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Check if the user exists and is blocked (is_active=False)
        if sociallogin.is_existing and not sociallogin.user.is_active:
            messages.error(request, "This account has been blocked by the admin. Please contact support.")
            
            # This "ImmediateHttpResponse" is the key. 
            # It kills the default flow and forces the redirect NOW.
            raise ImmediateHttpResponse(redirect('signup'))

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        return user