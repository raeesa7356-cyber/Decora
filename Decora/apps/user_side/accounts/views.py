from apps.core.utils import get_ui_avatar, generate_otp, send_custom_email,get_or_create_user_referral_code,apply_referral_code
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login,update_session_auth_hash
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from apps.admin_side.offers.models import ReferralOffer
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from .models import Profile,OTP,Address,Wallet,WalletTransaction,WalletRecharge
from django.views.decorators.cache import never_cache
from apps.admin_side.orders.models import Order
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
import razorpay
from django.conf import settings
from django.db import transaction
import re
from django.utils import timezone

MAX_OTP_ATTEMPTS = 5
OTP_LOCK_SECONDS = 15

def _otp_lock_status(request, prefix):
    locked_until = request.session.get(f'{prefix}_otp_locked_until')
    
    if not locked_until:
        return 0
    remaining = locked_until - timezone.now().timestamp()
    if remaining <= 0:
        request.session.pop(f'{prefix}_otp_locked_until', None)
        request.session[f'{prefix}_otp_attempts'] = 0
        return 0
    return int(remaining)


def _register_failed_otp_attempt(request, prefix):
    attempts = request.session.get(f'{prefix}_otp_attempts', 0) + 1
    request.session[f'{prefix}_otp_attempts'] = attempts
    if attempts >= MAX_OTP_ATTEMPTS:
        request.session[f'{prefix}_otp_locked_until'] = timezone.now().timestamp() + OTP_LOCK_SECONDS
        request.session[f'{prefix}_otp_attempts'] = 0
        return True
    return False


def _clear_otp_attempts(request, prefix):
    request.session.pop(f'{prefix}_otp_attempts', None)
    request.session.pop(f'{prefix}_otp_locked_until', None)
def landing(request):    
    if request.user.is_authenticated:
        return redirect('shop:home')
    return render(request, 'user_side/accounts/landing.html')

def signup_view(request):
    referral_code_prefill=""
    ref_token=request.GET.get('ref')
    if ref_token:
        referral=ReferralOffer.objects.filter(token=ref_token,referred_user__isnull=True,is_used=False).first()
        if referral:
            referral_code_prefill=referral.referral_code
            
    errors={}
    old_input={
        'fullname':'',
        'email':'',
        'password':'',
        'confirm_password':'',
        'referral_code':referral_code_prefill
    }
    if request.method=='POST':
        fullname=request.POST.get('fullname','').strip()
        email=request.POST.get('email','').strip()
        password=request.POST.get('password','')
        confirm_password=request.POST.get('confirm_password','')
        referral_code=request.POST.get('referral_code','').strip()
        if not fullname:
            errors['fullname']='Full name is required.'
        elif len(fullname)<2:    
            errors['fullname']='Full name must be at least 2 characters.'
        elif len(fullname)>50:
            errors['fullname'] ='Full name must be under 50 characters.'   
        elif not re.match(r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$",fullname):
            errors['fullname']='Full name can only contain letters, spaces, hyphens, and apostrophes.'   
        if User.objects.filter(email=email).exists():
            errors['email']='An account with this email already exists. Login to continue.'     
            
        pwd_problems=[]
        if len(password)<8:
            pwd_problems.append('at least 8 characters')
        if not any(char.isdigit() for char in password):
            pwd_problems.append('one number')
        if not any(char.isupper() for char in password):
            pwd_problems.append('one uppercase letter')
        if not any(char in '!@#$%^&*()_-+=' for char in password):
            pwd_problems.append('one special character')
        if pwd_problems:
            errors['password']='Password must conatin' + ','.join(pwd_problems)+'.'
        if password!=confirm_password:
            errors['confirm_password']='Passwords do not match.'           
                   
        

                                  
        old_input={
            'fullname':'' if errors.get('fullname') else fullname,
            'email':'' if errors.get('email') else email,
            'password':'' if errors.get('password') else password,
            'confirm_password':''if errors.get('confirm_password') else confirm_password,
            'referral_code':referral_code
        }
        if not errors:
            otp=generate_otp()
            subject='Verify your Decora Account'
            context={'otp':otp,'fullname':fullname}
            html_content=render_to_string('emails/signup_otp_email.html',context)
            email_sent=send_custom_email(subject,html_content,[email])

            if email_sent:
                request.session['signup_data']={
                    'fullname':fullname,
                    'email':email,
                    'otp': otp,
                    'password': password,   
                    'referral_code': referral_code      
                }
                return redirect('verify_otp')
            else:
                errors['non_field']='Could not send OTP. Please try again.'    
    return render(request,'user_side/accounts/signup.html',
                  { 'old_input':old_input,
                    'errors':errors, 
                    'referral_code_prefill':referral_code_prefill
                  })        
    
def verify_otp_view(request):
    if 'signup_data' not in request.session:
        return redirect('signup')

    lock_remaining = _otp_lock_status(request, 'signup')

    if request.method == "POST":
        if lock_remaining > 0:
            messages.error(request, "Too many attempts. Please check your email and try again.")
            return render(request, 'user_side/accounts/verify_otp.html', {'lock_remaining': lock_remaining})

        user_otp = request.POST.get('otp_code')
        session_data = request.session.get('signup_data')
        if user_otp == session_data['otp']:
            if User.objects.filter(username=session_data['email']).exists():
                messages.info(request, "Account already verified. Please log in.")
                request.session.pop('signup_data', None)
                _clear_otp_attempts(request, 'signup')
                return redirect('user_login')
            else:
                user = User.objects.create_user(
                    username=session_data['email'],
                    email=session_data['email'],
                    password=session_data['password'],
                    first_name=session_data['fullname']
                )
                referral_code = session_data.get('referral_code')
                if referral_code:
                    apply_referral_code(referral_code, user)

            request.session.pop('signup_data', None)
            _clear_otp_attempts(request, 'signup')
            messages.success(request, "Registration successful! Please log in to continue.")
            return redirect('user_login')
        else:
            just_locked = _register_failed_otp_attempt(request, 'signup')
            if just_locked:
                messages.error(request, "Too many attempts. Please check your email and try again.")
                return render(request, 'user_side/accounts/verify_otp.html', {'lock_remaining': OTP_LOCK_SECONDS})
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')

    return render(request, 'user_side/accounts/verify_otp.html', {'lock_remaining': lock_remaining})

def resend_otp(request):
    if 'reset_email' in request.session:
        email = request.session['reset_email']
        new_otp = generate_otp() 
        request.session['reset_otp'] = new_otp
        
        context = {'otp': new_otp, 'type': 'password reset'}
        html_content = render_to_string('emails/signup_otp_email.html', context)
        send_custom_email("Your New Decora Reset Code", html_content, [email]) 
        
        messages.success(request, "A new reset code has been sent.")
        return redirect('verify_reset_otp')

    elif 'signup_data' in request.session:
        session_data = request.session['signup_data']
        new_otp = generate_otp() 
        session_data['otp'] = new_otp
        request.session['signup_data'] = session_data
        
        context = {'otp': new_otp, 'fullname': session_data['fullname']}
        html_content = render_to_string('emails/signup_otp_email.html', context)
        send_custom_email("Your New Decora Verification Code", html_content, [session_data['email']]) 

        messages.success(request, "A new verification code has been sent.")
        return redirect('verify_otp')
        
    return redirect('login')
def login_view(request):

    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == "POST":
        email = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(username=email)

            if not user_obj.is_active:
                messages.error(request, "Your account has been disabled by Decora Admin.")
                return redirect('user_login')

        except User.DoesNotExist:
            messages.error(request, "Invalid credentials.")
            return redirect('user_login')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('shop:home')

        else:
            messages.error(request, "Invalid credentials.")
            return redirect('user_login')

    return render(request, 'user_side/accounts/login.html')

def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found.")
            return redirect('forgot_password')

        otp = generate_otp() 
        request.session['reset_email'] = email
        request.session['reset_otp'] = otp

        html_content = render_to_string('emails/signup_otp_email.html', {'otp': otp, 'type': 'password reset'})
        if send_custom_email("Reset your Decora Password", html_content, [email]):  
            messages.success(request, "Reset code sent.")
            return redirect('verify_reset_otp')
    
    return render(request, 'user_side/accounts/forgot_password.html')
def verify_reset_otp_view(request):
    if 'reset_email' not in request.session:
        return redirect('forgot_password')

    lock_remaining = _otp_lock_status(request, 'reset')

    if request.method == "POST":
        if lock_remaining > 0:
            messages.error(request, "Too many attempts. Please check your email and try again.")
            return render(request, 'user_side/accounts/verify_reset_otp.html', {'lock_remaining': lock_remaining})

        user_otp = request.POST.get('otp_code')
        session_otp = request.session.get('reset_otp')

        if user_otp == session_otp:
            _clear_otp_attempts(request, 'reset')
            return redirect('set_new_password')
        else:
            just_locked = _register_failed_otp_attempt(request, 'reset')
            if just_locked:
                messages.error(request, "Too many attempts. Please check your email and try again.")
                return render(request, 'user_side/accounts/verify_reset_otp.html', {'lock_remaining': OTP_LOCK_SECONDS})
            messages.error(request, "Invalid reset code. Please try again.")
            return redirect('verify_reset_otp')

    return render(request, 'user_side/accounts/verify_reset_otp.html', {'lock_remaining': lock_remaining})

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

    return render(request, 'user_side/accounts/set_new_password.html')
def reset_success_view(request):
    return render(request, 'user_side/accounts/reset_success.html')

def logout_view(request): 
    auth_logout(request)     
    return redirect('user_login')
@never_cache
@login_required
def profile_view(request):

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    addresses = Address.objects.filter(
    user=request.user
).order_by('-is_primary', '-id')

    latest_order = Order.objects.filter(
    user=request.user
).prefetch_related(
    'items'
).order_by(
    '-created_at'
).first()

    
    wallet, _ = Wallet.objects.get_or_create(
    user=request.user
)
    my_referral = get_or_create_user_referral_code(request.user)

    context = {
        'user': request.user,
        'profile': profile,
        'addresses': addresses,
        'wallet': wallet,
        'address_count': addresses.count(),
'latest_order': latest_order,
'my_referral': my_referral,

    }

    return render(
request,
'user_side/accounts/profile.html',
context
)
@never_cache
@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect('change_password')

        if not request.user.check_password(old_password):
            messages.error(request, "Your current password is incorrect.")
            return redirect('change_password')

        if old_password == new_password:
            messages.error(request, "Your new password cannot be the same as your current password. Please choose a different one.")
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')
        
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
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password updated successfully!")
        return redirect('profile')

    return render(request, 'user_side/accounts/change_password.html')
@never_cache
@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        request.user.first_name = request.POST.get('fullname')
        request.user.save()
        
        profile.phone = request.POST.get('phone')

        
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']
        
        if request.POST.get('delete_photo') == 'true':
            profile.profile_image = None
            
        profile.save()
        messages.success(request, "Profile updated!")
        return redirect('profile')

    return render(request, 'user_side/accounts/edit_profile.html', {'profile': profile})
@never_cache    
def change_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')  
        
        if User.objects.filter(username=new_email).exists():
            messages.error(request, "This email is already linked to another Decora account.")
            return redirect('change_email') 

        otp = generate_otp()
        OTP.objects.update_or_create(email=new_email, defaults={'otp': otp})
        request.session['pending_email'] = new_email 

        subject = "Verify your New Email - Decora"
        html_content = render_to_string('emails/otp_email.html', {'otp': otp})
        
        send_custom_email(subject, html_content, [new_email])

        return redirect('otp_verify')
    return render(request, 'user_side/accounts/change_email.html')
def verify_otp_email(request):
    new_email = request.session.get('pending_email')

    if not new_email:
        messages.error(request, 'sessiom expires ,please restart the process')
        return redirect('change_email')

    lock_remaining = _otp_lock_status(request, 'email')

    if request.method == 'POST':
        if lock_remaining > 0:
            messages.error(request, "Too many attempts. Please check your email and try again.")
            return render(request, 'user_side/accounts/verify_otp_email.html', {'lock_remaining': lock_remaining})

        entered_otp = request.POST.get('otp')
        otp_record = OTP.objects.filter(email=new_email, otp=entered_otp).first()
        if otp_record:
            user = request.user
            user.username = new_email
            user.email = new_email
            user.save()

            profile, created = Profile.objects.get_or_create(user=user)
            profile.is_verified = True
            profile.save()

            OTP.objects.filter(email=new_email).delete()
            if 'pending_email' in request.session:
                del request.session['pending_email']
            _clear_otp_attempts(request, 'email')
            messages.success(request, f"Identity updated to {new_email}")
            return redirect('email_success')
        else:
            just_locked = _register_failed_otp_attempt(request, 'email')
            if just_locked:
                messages.error(request, "Too many attempts. Please check your email and try again.")
                return render(request, 'user_side/accounts/verify_otp_email.html', {'lock_remaining': OTP_LOCK_SECONDS})
            messages.error(request, "Invalid OTP code. Please try again.")

    return render(request, 'user_side/accounts/verify_otp_email.html', {'lock_remaining': lock_remaining})
def resend_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "Session expired. Please restart.")
        return redirect('change_email')

    otp = generate_otp()
    OTP.objects.update_or_create(email=new_email, defaults={'otp': otp})

    subject = "Your New Decora Verification Code"
    html_content = render_to_string('emails/otp_email.html', {'otp': otp})
    send_custom_email(subject, html_content, [new_email])

    messages.success(request, f"A new code has been sent to {new_email}")
    return redirect('otp_verify') 
def email_change_success(request):
    return render(request, 'user_side/accounts/email_change_success.html')
@login_required
@never_cache
def manage_addresses(request):

    addresses = Address.objects.filter(user=request.user).order_by('-is_primary', '-id')

    if request.method == "POST":

        is_first_address = not Address.objects.filter(user=request.user).exists()
        is_primary = bool(request.POST.get('is_primary'))

        if is_first_address and not is_primary:
            messages.error(request, "Please set this as your default address since it's your first one.")
            return redirect('manage_addresses')

        if is_primary:
            Address.objects.filter(user=request.user).update(is_primary=False)

        address = Address(
    user=request.user,
    address_type=request.POST.get('address_type'),
    full_name=request.POST.get('full_name'),
    phone_number=request.POST.get('phone_number'),
    house_no=request.POST.get('house_no'),
    city=request.POST.get('city'),
    state=request.POST.get('state'),
    pincode=request.POST.get('pincode'),
    is_primary=is_primary
)
        try:
            address.full_clean()
        except ValidationError as e:
            messages.error(request, " ".join(sum(e.message_dict.values(), [])))
            return redirect('manage_addresses')
        address.save()

        messages.success(request, "New address added to your Decora profile.")
        return redirect('manage_addresses')

    return render(request, 'user_side/accounts/manage_address.html', {'addresses': addresses})
@login_required
def set_default_address(request, address_id):
    address = Address.objects.get(id=address_id, user=request.user)
    
    Address.objects.filter(user=request.user).update(is_primary=False)
    
    address.is_primary = True
    address.save()
    
    messages.success(request, f"'{address.address_type}' is now your default address.")
    return redirect('manage_addresses')
@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('manage_addresses')
@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == "POST":
        address_type = request.POST.get('address_type')
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        house_no = request.POST.get('house_no')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        is_primary = request.POST.get('is_primary') == 'on'

        
        if is_primary:
            Address.objects.filter(user=request.user).update(is_primary=False)

        address.address_type = address_type
        address.full_name = full_name
        address.phone_number = phone_number
        address.house_no = house_no
        address.city = city
        address.state = state
        address.pincode = pincode
        address.is_primary = is_primary
        try:
            address.full_clean()
        except ValidationError as e:
            messages.error(request, " ".join(sum(e.message_dict.values(), [])))
            return redirect('manage_addresses')

        address.save()

        messages.success(request, f"Address '{address.address_type}' updated successfully!")
        return redirect('manage_addresses')

    return redirect('manage_addresses')
@login_required
def order_list(request):

    orders = Order.objects.filter(
        user=request.user
    )

    status = request.GET.get("status")

    if status == "RETURNED":
        orders = orders.filter(
        items__status="RETURNED"
    ).distinct()

    elif status:
        orders = orders.filter(
        status=status
    )
    orders = orders.order_by("-created_at")

    return render(
    request,
    "user_side/accounts/order_list.html",
    {
        "orders": orders,
        "status": status,
    }
)
 
from .models import WalletTransaction, Wallet

@login_required
def wallet_view(request):

    wallet, _ = Wallet.objects.get_or_create(
        user=request.user
    )

    transactions = (
        WalletTransaction.objects
        .filter(wallet=wallet)
        .order_by('-created_at')
    )

    return render(
request,
'user_side/accounts/wallet.html',
{
    'wallet': wallet,
    'transactions': transactions
}
)      
@login_required
def add_money_view(request):

    if request.method == "POST":

        amount = request.POST.get("amount")

        try:
            amount = int(amount)
        except:
            messages.error(
                request,
                "Invalid amount"
            )
            return redirect("add_money")

        if amount < 1:
            messages.error(request, "Amount must be greater than zero")
            return redirect("add_money")

        max_amount = getattr(settings, 'RAZORPAY_MAX_TRANSACTION_AMOUNT', 25000)
        if amount > max_amount:
            messages.error(
        request,
        "Online payment cannot be processed because the transaction amount exceeds the ₹25,000 limit."
    )
            return redirect("add_money")

        client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


        razorpay_order = client.order.create({
            "amount": amount * 100,
            "currency": "INR"
        })

        WalletRecharge.objects.create(
            user=request.user,
            amount=amount,
            razorpay_order_id=razorpay_order["id"]
        )

        return render(
        request,
        "user_side/accounts/razorpay_payment.html",
        {
            "amount": amount,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "user": request.user
        }
    )

    return render(
        request,
        "user_side/accounts/add_money.html"
    )

@csrf_exempt

def verify_wallet_payment(request):

    if request.method != "POST":
        return redirect("wallet")

    razorpay_order_id = request.POST.get(
        "razorpay_order_id"
    )

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id"
    )

    razorpay_signature = request.POST.get(
        "razorpay_signature"
    )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        recharge = WalletRecharge.objects.get(
            razorpay_order_id=razorpay_order_id
        )

        if recharge.status != "SUCCESS":

            with transaction.atomic():

                recharge.status = "SUCCESS"
                recharge.razorpay_payment_id = razorpay_payment_id
                recharge.razorpay_signature = razorpay_signature
                recharge.save()

                wallet, _ = Wallet.objects.get_or_create(
                    user=recharge.user
                )

                wallet.balance += recharge.amount
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=recharge.amount,
                    transaction_type="credit",
                    purpose="wallet_recharge"
                )

        return redirect(
            "wallet_payment_success",
            recharge.id
        )

    except Exception as e:

     

        return redirect(
"wallet_payment_failed"
)
@login_required
def wallet_payment_success(
    request,
    recharge_id
):

    recharge = get_object_or_404(
        WalletRecharge,
        id=recharge_id,
        user=request.user
    )

    return render(
request,
"user_side/accounts/wallet_success.html",
{
    "recharge": recharge
}
)
@login_required
def wallet_payment_failed(request):

    return render(
request,
"user_side/accounts/wallet_failed.html"
)
def referral_redirect(request, token):
    return redirect(f"/signup/?ref={token}")    