import random
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
from .models import Profile,OTP,Address
from django.core.mail import send_mail
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
def landing(request):
    
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'accounts/landing.html')

def signup_view(request):
    #submitting the form
    if request.method == "POST":
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        #validations
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.login to continue")
            return redirect('signup')

        if User.objects.filter(email=email, is_staff=True).exists():
            messages.error(request, "This email is registered to an administrative account and cannot be used for customer signup.")
            return redirect('signup')
        #password validations
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('signup')
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('signup')


        if not any(char.isdigit() for char in password):
            messages.error(request, "Password must contain at least one number.")
            return redirect('signup')

        if not any(char.isupper() for char in password):
            messages.error(request, "Password must contain at least one uppercase letter.")
            return redirect('signup')

        if not any(char in "!@#$%^&*()_+-=" for char in password):
            messages.error(request, "Password must contain at least one special character (!@#$%^&*).")
            return redirect('signup')
        #otp generation
        otp = str(random.randint(100000, 999999))
        
        # Email Details
        subject = "Confirm your Decora Account"
        from_email = settings.EMAIL_HOST_USER
        to = email

        
        context = {'otp': otp, 'fullname': fullname}
        html_content = render_to_string('emails/signup_otp_email.html', context)
        text_content = strip_tags(html_content)
    # email sending
        try:
         
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            
        
            msg.extra_headers['X-Entity-Ref-ID'] = str(random.randint(1, 10000))
            
            msg.send(fail_silently=False)
    # storing into session
            request.session['signup_data'] = {
                'fullname': fullname,
                'email': email,
                'password': password,
                'otp': otp 
            }
            return redirect('verify_otp')

        except Exception as e:
            print(f"DETAILED EMAIL ERROR: {e}")
            messages.error(request, "Could not send OTP. Please try again later.")
            return redirect('signup')

    return render(request, 'accounts/signup.html')
def verify_otp_view(request):
    # check user data in session or not
    if 'signup_data' not in request.session:
        return redirect('signup')
    # submitting
    if request.method == "POST":
        user_otp = request.POST.get('otp_code')
        session_data = request.session.get('signup_data')
# check otp is match or not
        if user_otp == session_data['otp']:
            # check the email already exists
            if User.objects.filter(username=session_data['email']).exists():
                messages.info(request, "Account already verified. Please log in.")
                request.session.pop('signup_data', None)
                return redirect('login')

        # creating user
            else:
                user=User.objects.create_user(
                username=session_data['email'],
                email=session_data['email'],
                password=session_data['password'],
                first_name=session_data['fullname']
                )
                # removes session data
            request.session.pop('signup_data', None)
            
            messages.success(request, "Registration successful! Please log in to continue.")
            return redirect('login') 
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')

    return render(request, 'accounts/verify_otp.html')

def resend_otp(request):
    # Case 1: Password Reset Resend
    if 'reset_email' in request.session:
        email = request.session['reset_email']
        new_otp = str(random.randint(100000, 999999))
        request.session['reset_otp'] = new_otp
        
        # ACTUALLY SEND THE EMAIL
        subject = "Your New Decora Reset Code"
        context = {'otp': new_otp, 'type': 'password reset'}
        html_content = render_to_string('emails/signup_otp_email.html', context)
        msg = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        messages.success(request, "A new reset code has been sent.")
        return redirect('verify_reset_otp')

    # Case 2: Signup Resend
    elif 'signup_data' in request.session:
        session_data = request.session['signup_data']
        new_otp = str(random.randint(100000, 999999))
        
        # Update the session with the new OTP
        session_data['otp'] = new_otp
        request.session['signup_data'] = session_data
        
        # ACTUALLY SEND THE EMAIL
        subject = "Your New Decora Verification Code"
        context = {'otp': new_otp, 'fullname': session_data['fullname']}
        html_content = render_to_string('emails/signup_otp_email.html', context)
        msg = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [session_data['email']])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        messages.success(request, "A new verification code has been sent.")
        return redirect('verify_otp')
    return redirect('login')
def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get('username') 
        password = request.POST.get('password')
       
        user = authenticate(email=email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('home')
            else:
     
                messages.error(request, "Your account has been disabled by the Decora Admin.")
                return redirect('login')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'accounts/login.html')


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        
       
        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found with this email.")
            return redirect('forgot_password')

       
        otp = str(random.randint(100000, 999999))
        request.session['reset_email'] = email
        request.session['reset_otp'] = otp

     
        subject = "Reset your Decora Password"
        context = {'otp': otp, 'type': 'password reset'}
        html_content = render_to_string('emails/signup_otp_email.html', context) # You can reuse your signup email template
        
        try:
            msg = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            messages.success(request, "Reset code sent to your email.")
            return redirect('verify_reset_otp') # You'll create this next
        except Exception as e:
            messages.error(request, "Error sending email.")
    
    return render(request, 'accounts/forgot_password.html')
def verify_reset_otp_view(request):
    if 'reset_email' not in request.session:
        return redirect('forgot_password')

    if request.method == "POST":
        user_otp = request.POST.get('otp_code')
        session_otp = request.session.get('reset_otp')

        if user_otp == session_otp:
            return redirect('set_new_password')
        else:
            messages.error(request, "Invalid reset code. Please try again.")
            return redirect('verify_reset_otp')

    return render(request, 'accounts/verify_reset_otp.html')


def set_new_password_view(request):
    if 'reset_email' not in request.session:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forgot_password')

    if request.method == "POST":
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('set_new_password')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect('set_new_password')
        
        if not any(char.isdigit() for char in new_password) or \
           not any(char.isupper() for char in new_password) or \
           not any(char in "!@#$%^&*()_+-=" for char in new_password):
            messages.error(request, "Password must include uppercase, number, and special character.")
            return redirect('set_new_password')

        try:
            email = request.session.get('reset_email')
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            request.session.pop('reset_email', None)
            request.session.pop('reset_otp', None)

            messages.success(request, "Password reset successful! Please login with your new password or back to home to explore.")
            return redirect('reset_success')
        except User.DoesNotExist:
            messages.error(request, "An error occurred. Please try again.")
            return redirect('forgot_password')

    return render(request, 'accounts/set_new_password.html')
def reset_success_view(request):
    return render(request, 'accounts/reset_success.html')
@never_cache
@login_required(login_url='login')
def home_view(request):
    return render(request,'accounts/home.html')
def logout_view(request): 
    auth_logout(request)  
    return redirect('login')
@never_cache
@login_required
def profile_view(request):
    # Fetch up to 2 addresses for the profile preview
    addresses = Address.objects.filter(user=request.user).order_by('-is_primary', '-id')[:2]
    
    context = {
        'user': request.user,
        'addresses': addresses,
        'address_count': addresses.count(),
    }
    return render(request, 'accounts/profile.html', context)


@never_cache
@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # 1. Basic Validation
        if not all([old_password, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect('change_password')

        # 2. Check if old password is correct
        if not request.user.check_password(old_password):
            messages.error(request, "Your current password is incorrect.")
            return redirect('change_password')

        # 3. NEW CHECK: Prevent using the same password
        if old_password == new_password:
            messages.error(request, "Your new password cannot be the same as your current password. Please choose a different one.")
            return redirect('change_password')

        # 4. Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')
        
        # 5. Strength Validation
        if len(new_password) < 8:
            messages.error(request, "New password must be at least 8 characters.")
            return redirect('change_password')
        if not any(char.isdigit() for char in new_password):
            messages.error(request, "Password must contain at least one number.")
            return redirect('change_password')

        if not any(char.isupper() for char in new_password):
            messages.error(request, "Password must contain at least one uppercase letter.")
            return redirect('change_password')

        if not any(char in "!@#$%^&*()_+-=" for char in new_password):
            messages.error(request, "Password must contain at least one special character (!@#$%^&*).")
            return redirect('change_password')
        # 6. Success: Update Password
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password updated successfully!")
        return redirect('profile')

    return render(request, 'accounts/change_password.html')
@never_cache
@login_required
def edit_profile(request):
    # 1. Get or create the profile linked to the current logged-in user
    # request.user is already the User instance you need.
    profile, created = Profile.objects.get_or_create(user=request.user)
    user_instance = request.user 

    if request.method == "POST":
        # Update User model data
        user_instance.first_name = request.POST.get('fullname')
        user_instance.save()
        
        # Update Profile model data
        phone = request.POST.get('phone')
        profile.phone = phone
        
        if 'profile_pic' in request.FILES:
            profile.profile_image = request.FILES['profile_pic']
            
        if request.POST.get('delete_photo') == 'true':
            profile.profile_image = None
            
        profile.save()
        messages.success(request, "Profile updated!")
        return redirect('profile')

    return render(request, 'accounts/edit_profile.html', {
        'profile': profile,
        'user': user_instance
    })
@never_cache    
def change_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')  
        
        if User.objects.filter(username=new_email).exists():
            messages.error(request, "This email is already linked to another Decora account.")
            return redirect('change_email') 
        otp = str(random.randint(100000, 999999))
        
        OTP.objects.update_or_create(email=new_email, defaults={'otp': otp})
        request.session['pending_email'] = new_email 

        # Sending HTML Email
        subject = "Verify your New Email - Decora"
        html_content = render_to_string('emails/otp_email.html', {'otp': otp})
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [new_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return redirect('otp_verify')
    return render(request, 'accounts/change_email.html')
def verify_otp_email(request):
    new_email=request.session.get('pending_email')
    
    if not new_email:
        messages.error(request,'sessiom expires ,please restart the process')
        return redirect('change_email')
    if request.method=='POST':
        entered_otp=request.POST.get('otp')
        otp_record=OTP.objects.filter(email=new_email,otp=entered_otp).first()
        if otp_record:
            # 1. Update the User (Username & Email)
            user = request.user
            user.username = new_email
            user.email = new_email
            user.save()

            # 2. Update Profile verification status
            profile, created = Profile.objects.get_or_create(user=user)
            profile.is_verified = True
            profile.save()

            # 3. Success cleanup
            
            OTP.objects.filter(email=new_email).delete()   
            if 'pending_email' in request.session:
                del request.session['pending_email']            
            messages.success(request, f"Identity updated to {new_email}")
            return redirect('email_success')
        else:
            messages.error(request, "Invalid OTP code. Please try again.")

    return render(request, 'accounts/verify_otp_email.html')
# views.py

def resend_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "Session expired. Please restart the process.")
        return redirect('change_email')

    # Generate new OTP
    otp = str(random.randint(100000, 999999))
    OTP.objects.update_or_create(email=new_email, defaults={'otp': otp})

    # Send Email
    subject = "Your New Decora Verification Code"
    html_content = render_to_string('emails/otp_email.html', {'otp': otp})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [new_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    messages.success(request, f"A new code has been sent to {new_email}")
    return redirect('otp_verify') # Stays on the verification page
def email_change_success(request):
    return render(request, 'accounts/email_change_success.html')
@never_cache
@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user).order_by('-is_primary', '-id')
    
    if request.method == "POST":
        # Logic for adding a new address
        Address.objects.create(
            user=request.user,
            address_type=request.POST.get('address_type'),
            full_name=request.POST.get('full_name'),
            phone_number=request.POST.get('phone_number'),
            house_no=request.POST.get('house_no'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            pincode=request.POST.get('pincode'),
            is_primary=request.POST.get('is_primary') == 'on'
        )
        messages.success(request, "New address added to your Decora profile.")
        return redirect('manage_addresses')

    return render(request, 'accounts/manage_address.html', {'addresses': addresses})
@login_required
def set_default_address(request, address_id):
    # 1. Get the address the user clicked on
    address = Address.objects.get(id=address_id, user=request.user)
    
    # 2. Set all user's addresses to False
    Address.objects.filter(user=request.user).update(is_primary=False)
    
    # 3. Set this specific one to True
    address.is_primary = True
    address.save()
    
    messages.success(request, f"'{address.address_type}' is now your default address.")
    return redirect('manage_addresses')
def delete_address(request, address_id):
    # Only allow the logged-in user to delete their own address
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('manage_addresses')
@login_required
def edit_address(request, address_id):
    # 1. Fetch the specific address or return 404 if it doesn't exist/belong to the user
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == "POST":
        # 2. Extract updated data from the form
        address_type = request.POST.get('address_type')
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        house_no = request.POST.get('house_no')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        is_primary = request.POST.get('is_primary') == 'on'

        # 3. Handle Primary Logic: If this address is set to primary, 
        # unset all other addresses for this user first.
        if is_primary:
            Address.objects.filter(user=request.user).update(is_primary=False)

        # 4. Update the fields
        address.address_type = address_type
        address.full_name = full_name
        address.phone_number = phone_number
        address.house_no = house_no
        address.city = city
        address.state = state
        address.pincode = pincode
        address.is_primary = is_primary
        
        address.save()

        messages.success(request, f"Address '{address.address_type}' updated successfully!")
        return redirect('manage_addresses')

    # If it's a GET request, we just redirect back (or you can render the page)
    return redirect('manage_addresses')
