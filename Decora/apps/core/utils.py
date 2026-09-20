import os
import uuid
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from apps.admin_side.offers.models import ProductOffer, CategoryOffer
from apps.admin_side.offers.models import ReferralOffer
from django.conf import settings
from apps.admin_side.offers.models import ReferralOffer
from django.core.mail import send_mail
from django.conf import settings
import traceback
from django.core.mail import EmailMultiAlternatives
from decimal import Decimal
from django.db.models import Avg, Count

def get_product_rating_stats(product):
    from apps.user_side.orders.models import Review  

    stats = Review.objects.filter(
    product=product,
    is_approved=True,
    is_visible=True,
    ).aggregate(
    avg_rating=Avg('rating'),
    review_count=Count('id'),
    )
    avg = stats['avg_rating'] or 0.0
    count = stats['review_count'] or 0
    return round(avg, 1), count

def get_ui_avatar(name, background="1a1a1a", color="D4AF37"):
    clean_name = name.replace(" ", "+")
    return f"https://ui-avatars.com/api/?name={clean_name}&background={background}&color={color}&bold=true&size=128"

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_custom_email(subject, message, recipient_list):
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body="Please view this email in an HTML-compatible client.",  
            from_email=settings.EMAIL_HOST_USER,
            to=recipient_list,
        )
        email.attach_alternative(message, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        traceback.print_exc()
        return False

def profile_image_path(instance, filename):
    ext = filename.split('.')[-1]
    unique_name = f"{instance.user.username}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('profile_pics/', unique_name)

def get_best_offer_discount_amount(product, base_price):
    now = timezone.now()
    
    product_offer = ProductOffer.objects.filter(
        product=product, is_active=True,
        valid_from__lte=now, valid_until__gte=now
    ).order_by('-discount_percent').first()
    
    category_offer = CategoryOffer.objects.filter(
        category=product.category, is_active=True,
        valid_from__lte=now, valid_until__gte=now
    ).order_by('-discount_percent').first()

    def _resolve(offer):
        if not offer:
            return Decimal("0")
        if offer.discount_type == "fixed":
            return Decimal(offer.discount_percent)
        else: 
            return base_price * Decimal(offer.discount_percent) / Decimal("100")

    product_amt = _resolve(product_offer)
    category_amt = _resolve(category_offer)

    best = max(product_amt, category_amt)
    return min(best, base_price) 


def get_best_offer_display(product):
    now = timezone.now()

    product_offer = ProductOffer.objects.filter(
        product=product, is_active=True,
        valid_from__lte=now, valid_until__gte=now
    ).order_by('-discount_percent').first()

    category_offer = CategoryOffer.objects.filter(
        category=product.category, is_active=True,
        valid_from__lte=now, valid_until__gte=now
    ).order_by('-discount_percent').first()

    candidates = [o for o in (product_offer, category_offer) if o]
    if not candidates:
        return None, None

    
    fixed_offers = [o for o in candidates if o.discount_type == "fixed"]
    if fixed_offers:
        best = max(fixed_offers, key=lambda o: o.discount_percent)
        return f"₹{int(best.discount_percent)} OFF", best

    best = max(candidates, key=lambda o: o.discount_percent)
    return f"{int(best.discount_percent)}% OFF", best


def get_combination_pricing(combination, coupon_discount=Decimal("0")):
    original_price = Decimal(combination.original_price or 0)

    if combination.discount_price is not None and combination.discount_price < original_price:
        base_final = Decimal(combination.discount_price)
    else:
        base_final = original_price

    combo_discount = original_price - base_final
    offer_discount = get_best_offer_discount_amount(combination.product, base_final)

    final_price = base_final - offer_discount - coupon_discount
    final_price = max(final_price, Decimal("0"))

    return {
    "original_price": original_price,
    "combo_discount": combo_discount,
    "offer_discount": offer_discount,
    "coupon_discount": coupon_discount,
    "final_price": final_price,
    }
    
def generate_referral_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return 'DEC' + ''.join(random.choices(chars, k=length))

def get_or_create_user_referral_code(user, reward_amount=None):
    existing = ReferralOffer.objects.filter(
        referrer=user, referred_user__isnull=True
    ).first()
    
    if existing:
        return existing

    if reward_amount is None:
        reward_amount = getattr(settings, "REFERRAL_REWARD_AMOUNT", 100)

    code = generate_referral_code()
    while ReferralOffer.objects.filter(referral_code=code).exists():
        code = generate_referral_code()

    return ReferralOffer.objects.create(
    referrer=user,
    referral_code=code,
    token=uuid.uuid4().hex,
    reward_amount=reward_amount,
)
    


def apply_referral_code(code, new_user):
    from apps.user_side.accounts.models import Wallet, WalletTransaction

    if not code:
        return False

    referral = ReferralOffer.objects.filter(
        referral_code__iexact=code.strip(),
        referred_user__isnull=True,
        is_used=False,
    ).first()

    if not referral:
        return False

    if referral.referrer_id == new_user.id:
        return False   

    referral.referred_user = new_user
    referral.is_used = True
    referral.save()
    
    wallet, _ = Wallet.objects.get_or_create(user=referral.referrer)
    wallet.balance += referral.reward_amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=referral.reward_amount,
        transaction_type="credit",
        purpose="referral_bonus",
    )

    return True
        