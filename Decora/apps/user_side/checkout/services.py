from decimal import Decimal
from django.db import transaction
from apps.admin_side.catalog.models import VariantCombination
from apps.core.utils import get_combination_pricing
from apps.admin_side.orders.models import Order, OrderItem
from apps.admin_side.orders.models import OrderPayment
import razorpay
from django.conf import settings
from django.utils import timezone
from apps.admin_side.coupons.models import Coupon, CouponUsage
from apps.user_side.accounts.models import Wallet, WalletTransaction


class BuyNowItem:
    """
    A cart-shaped stand-in used for the buy-now flow, so checkout code can
    treat a real Cart row and a buy-now session the same way — both just
    need .product, .combination, .quantity, and a no-op .delete().
    """
    def __init__(self, product, combination, quantity):
        self.product = product
        self.combination = combination
        self.quantity = quantity

    def delete(self):
        pass


def get_cart_item_data(item):
    combo = item.combination
    color_variant = combo.variants.filter(variant_type='Color').first()

    variant_display = " / ".join(
        v.variant_value.upper() for v in combo.variants.all()
    )

    pricing = get_combination_pricing(combo)
    final_price = pricing["final_price"]
    original_price = pricing["original_price"]
    item_total = final_price * item.quantity
    original_item_total = original_price * item.quantity

    return {
"combination": combo,
"image_variant": color_variant,
"variant_display": variant_display,
"final_price": final_price,
"original_price": original_price,
"item_total": item_total,
"original_item_total": original_item_total,
}


def calculate_checkout_totals(cart_items):
    subtotal = Decimal("0")
    original_total = Decimal("0")

    for item in cart_items:
        subtotal += item.item_total
        original_total += (item.original_price * item.quantity)

    saved_amount = original_total - subtotal
    shipping = Decimal("0")
    total = subtotal + shipping

    return {
    "subtotal": subtotal,
    "original_total": original_total,
    "saved_amount": saved_amount,
    "shipping": shipping,
    "total": total,
}


def prepare_checkout_items(cart_items):
    for item in cart_items:
        data = get_cart_item_data(item)
        item.image_variant = data["image_variant"]
        item.variant_display = data["variant_display"]
        item.final_price = data["final_price"]
        item.original_price = data["original_price"]
        item.item_total = data["item_total"]
    return cart_items


@transaction.atomic
def create_order(*, user, address, cart_items, payment_method="COD", coupon_discount=Decimal("0")):
    totals = calculate_checkout_totals(cart_items)
    final_total = max(totals["total"] - coupon_discount, 0)

    if payment_method == "WALLET":
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if wallet.balance < final_total:
            raise ValueError("Insufficient wallet balance. Please recharge your wallet.")

    order = Order.objects.create(
        user=user,
        address=address,
        delivery_full_name=address.full_name,
        delivery_phone=address.phone_number,
        delivery_house_no=address.house_no,
        delivery_city=address.city,
        delivery_state=address.state,
        delivery_pincode=address.pincode,
        subtotal=totals["subtotal"],
        shipping_charge=totals["shipping"],
        discount_amount=totals["saved_amount"] + coupon_discount,
        total_amount=final_total,
        payment_method=payment_method,
        status="PENDING",
    )

    if payment_method == "RAZORPAY":
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rp_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "payment_capture": 1,
        })
        OrderPayment.objects.create(order=order, razorpay_order_id=rp_order["id"], status="PENDING")

    elif payment_method == "WALLET":
        wallet.balance -= final_total
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet, amount=final_total,
            transaction_type="debit", purpose="order_payment",
        )

    for item in cart_items:
        data = get_cart_item_data(item)

                    # lock the real combination row so concurrent orders can't oversell it
        combo = VariantCombination.objects.select_for_update().get(id=item.combination.id)

        if combo.stock_quantity < item.quantity:
            raise ValueError(f"{item.product.name} is out of stock")

        OrderItem.objects.create(
            order=order,
            product=item.product,
            combination=combo,
            quantity=item.quantity,
            price=data["final_price"],
            total_price=data["item_total"],
        )

        combo.stock_quantity -= item.quantity
        combo.save()

        item.delete()

    return order


def validate_and_get_coupon(code, user, cart_items, subtotal):
    now = timezone.now()
    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True, is_deleted=False)
    except Coupon.DoesNotExist:
        raise ValueError("Invalid coupon code.")

    if not (coupon.valid_from <= now <= coupon.valid_until):
        raise ValueError("This coupon has expired or is not yet active.")
    if subtotal < coupon.min_order_value:
        raise ValueError(f"Minimum order value of ₹{coupon.min_order_value} required.")
    if coupon.total_usage_limit and coupon.total_used_count >= coupon.total_usage_limit:
        raise ValueError("This coupon has reached its usage limit.")
    if coupon.usage_limit_per_user:
        if CouponUsage.objects.filter(coupon=coupon, user=user).count() >= coupon.usage_limit_per_user:
            raise ValueError("You have already used this coupon the maximum number of times.")

    return coupon


def calculate_coupon_discount(coupon, order_total):
    if coupon.discount_type == 'percentage':
        discount = (order_total * coupon.discount_amount) / Decimal("100")
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
    else:
        discount = coupon.discount_amount
    return discount


def get_available_coupons(user, subtotal):
    now = timezone.now()
    coupons = Coupon.objects.filter(
        is_active=True, is_deleted=False,
        valid_from__lte=now, valid_until__gte=now,
        min_order_value__lte=subtotal,
    )
    eligible = []
    for coupon in coupons:
        if coupon.total_usage_limit and coupon.total_used_count >= coupon.total_usage_limit:
            continue
        if coupon.usage_limit_per_user:
            if CouponUsage.objects.filter(coupon=coupon, user=user).count() >= coupon.usage_limit_per_user:
                continue
        eligible.append(coupon)
    return eligible