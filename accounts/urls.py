from django.urls import path
from . import views

urlpatterns = [
    # Auth Pages
path('', views.landing, name='landing'),
path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
  
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    # # Landing & Main Pages
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp_view, name='verify_reset_otp'),
    path('set-new-password/', views.set_new_password_view, name='set_new_password'),
    path('reset-success/', views.reset_success_view, name='reset_success'),
    path('logout/',views.logout_view,name='logout-page'),
# Logged in users go here# Next step
    path('home/', views.home_view, name='home'),# Next step
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
path('edit-profile/', views.edit_profile, name='edit_profile'),
path('change-email/', views.change_email, name='change_email'),
path('verify-email/', views.verify_otp_email, name='otp_verify'),
path('email-updated/', views.email_change_success, name='email_success'),
path('manage-address/',views.manage_addresses,name='manage_addresses'),
path('address/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
path('resend-email-otp/', views.resend_email_otp, name='resend_email_otp'),
    # path('shop/', views.shop_view, name='shop'),
    # path('inspiration/', views.inspiration_view, name='inspiration'),
    # path('contact/', views.contact_view, name='contact'),
    
    # # User Specific (Will be protected later)
    # path('profile/', views.profile_view, name='profile'),
    # path('cart/', views.cart_view, name='cart'),
    # path('wishlist/', views.wishlist_view, name='wishlist'),
]