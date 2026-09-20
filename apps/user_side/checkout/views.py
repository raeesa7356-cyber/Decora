from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.user_side.cart.models import Cart
from apps.user_side.accounts.models import Address
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import json
from django.views.decorators.http import require_POST
from apps.admin_side.orders.models import Order, OrderPayment
from apps.admin_side.catalog.models import Product, VariantCombination
from .services import (
    BuyNowItem,
    calculate_checkout_totals,
    create_order,
    prepare_checkout_items,
    calculate_coupon_discount,
    get_available_coupons,
    validate_and_get_coupon,
)
from django.views.decorators.csrf import csrf_exempt
import razorpay
from apps.user_side.accounts.models import Wallet
from apps.admin_side.coupons.models import Coupon, CouponUsage
from django.conf import settings


def _build_buy_now_items(buy_now_data):
    try:
        product = Product.objects.get(id=buy_now_data["product_id"], is_active=True)
        combination_id = buy_now_data["combination_id"]
        quantity = int(buy_now_data["quantity"])
    except (Product.DoesNotExist, KeyError, ValueError):
        return None

    combination = VariantCombination.objects.filter(
        id=combination_id, product=product, is_active=True
    ).first()
    if not combination:
        return None

    item = BuyNowItem(product=product, combination=combination, quantity=quantity)
    return prepare_checkout_items([item])


@login_required
def checkout(request):
    buy_now_data = request.session.get("buy_now")
    is_buy_now = bool(buy_now_data)

    if request.method == "POST" and request.POST.get("add_address"):
        is_first_address = not Address.objects.filter(user=request.user).exists()
        make_default = bool(request.POST.get("is_primary"))

        if is_first_address and not make_default:
            messages.error(request, "Please set this as your default address since it's your first one.")
            return redirect("checkout")

        if make_default:
            Address.objects.filter(user=request.user).update(is_primary=False)

        Address.objects.create(
            user=request.user,
            address_type=request.POST.get("address_type", "Home"),
            full_name=request.POST.get("full_name"),
            phone_number=request.POST.get("phone"),
            house_no=request.POST.get("address_line_1"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            pincode=request.POST.get("pincode"),
            is_primary=make_default,
        )
        return redirect("checkout")

    if request.method == "POST" and request.POST.get("edit_address"):
        address = Address.objects.get(id=request.POST.get("address_id"), user=request.user)
        address.is_primary = False
        if request.POST.get("is_primary"):
            Address.objects.filter(user=request.user).update(is_primary=False)
        address.is_primary = True
        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone")
        address.house_no = request.POST.get("address_line_1")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.save()
        return redirect("checkout")

    if is_buy_now:
        cart_items = _build_buy_now_items(buy_now_data)
        if not cart_items:
            request.session.pop("buy_now", None)
            messages.error(request, "That product is no longer available.")
            return redirect("shop:product-list")
    else:
        cart_items = (
            Cart.objects
            .select_related("product", "combination")
            .prefetch_related("combination__variants")
            .filter(user=request.user)
        )
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("cart:cart")

        cart_items = prepare_checkout_items(cart_items)

                    # ── Stock filter — each combination already carries its own stock ──
    available_items = [item for item in cart_items if item.combination.stock_quantity > 0]
    cart_items = available_items

    if not cart_items:
        if is_buy_now:
            request.session.pop("buy_now", None)
            messages.error(request, "That product is currently out of stock.")
            return redirect("shop:product-list")
        else:
            messages.error(request, "All items in your cart are currently out of stock.")
            return redirect("cart:cart")

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_primary=True).first()
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    totals = calculate_checkout_totals(cart_items)

    available_coupons = get_available_coupons(request.user, totals["subtotal"])
    coupon_discount = Decimal("0")
    applied_coupon = None
    coupon_id = request.session.get("applied_coupon_id")
    if coupon_id:
        applied_coupon = Coupon.objects.filter(id=coupon_id, is_active=True, is_deleted=False).first()
        if applied_coupon:
            coupon_discount = calculate_coupon_discount(applied_coupon, totals["total"])
            totals["coupon_discount"] = coupon_discount
            totals["total"] = max(totals["total"] - coupon_discount, 0)

    if request.method == "POST":
        address_id = request.POST.get("address")
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect("checkout")

        address = Address.objects.get(id=address_id, user=request.user)
        payment_method = request.POST.get("payment_method", "COD")

                                    # Final stock check before committing
        for item in cart_items:
            if item.combination.stock_quantity < item.quantity:
                messages.error(request, f"Cannot place order. '{item.product.name}' is currently out of stock.")
                if is_buy_now:
                    return redirect("shop:product_detail", pk=buy_now_data["product_id"])
                return redirect("cart:cart")

        try:
            order = create_order(
                user=request.user,
                address=address,
                cart_items=cart_items,     # BuyNowItem.delete() is a no-op — cart untouched
                payment_method=payment_method,
                coupon_discount=coupon_discount,
            )

            if applied_coupon:
                CouponUsage.objects.create(coupon=applied_coupon, user=request.user, order=order)
                request.session.pop("applied_coupon_id", None)

            if is_buy_now:
                request.session.pop("buy_now", None)

        except ValueError as e:
            messages.error(request, str(e))
            if is_buy_now:
                return redirect("shop:product_detail", pk=buy_now_data["product_id"])
            return redirect("cart:cart")

        if payment_method == "COD":
            return redirect(reverse("order_success", args=[order.id]))
        elif payment_method == "RAZORPAY":
            return redirect(reverse("checkout_payment", args=[order.id]))
        elif payment_method == "WALLET":
            return redirect(reverse("order_success", args=[order.id]))

    context = {
        "cart_items": cart_items,
        "addresses": addresses,
        "default_address": default_address,
        "wallet": wallet,
        "applied_coupon": applied_coupon,
        "available_coupons": available_coupons,
        "is_buy_now": is_buy_now,
        **totals,
    }
    return render(request, "user_side/checkout/checkout.html", context)


                                                # ─────────────────────────────────────────────────────────────────────────
                                                # Other views — unchanged
                                                # ─────────────────────────────────────────────────────────────────────────

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user_side/checkout/order_success.html', {'order': order})


@login_required
@require_POST
def set_default_address(request):
    data = json.loads(request.body)
    address_id = data.get("address_id")
    Address.objects.filter(user=request.user).update(is_primary=False)
    Address.objects.filter(id=address_id, user=request.user).update(is_primary=True)
    return JsonResponse({"success": True})


@login_required
def checkout_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    payment = OrderPayment.objects.filter(order=order).first()
    if not payment:
        rp_order = client.order.create({"amount": int(order.total_amount * 100), "currency": "INR"})
        payment = OrderPayment.objects.create(order=order, razorpay_order_id=rp_order["id"])

    return render(request, "user_side/checkout/payment.html", {
    "order": order,
    "razorpay_order_id": payment.razorpay_order_id,
    "razorpay_key": settings.RAZORPAY_KEY_ID,
    "razorpay_amount": int(order.total_amount * 100),
})


import json as json_lib  # avoid clashing with your existing `import json` if present elsewhere in the file

@csrf_exempt
def verify_order_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    # Success case: Razorpay sends a flat razorpay_order_id field.
    razorpay_order_id = request.POST.get("razorpay_order_id")

    # Failure case: order_id is nested inside a JSON STRING under error[metadata].
    if not razorpay_order_id:
        error_metadata_raw = request.POST.get("error[metadata]")
        if error_metadata_raw:
            try:
                error_metadata = json_lib.loads(error_metadata_raw)
                razorpay_order_id = error_metadata.get("order_id")
                if not razorpay_payment_id:
                    razorpay_payment_id = error_metadata.get("payment_id")
            except (ValueError, TypeError):
                pass

    if not razorpay_order_id:
        return redirect("checkout")

    payment = OrderPayment.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not payment:
            return redirect("checkout")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                })
        payment.status = "SUCCESS"
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.save()
        payment.order.status = "PENDING"
        payment.order.save()
        return redirect("order_success", payment.order.id)

    except Exception:
        payment.status = "FAILED"
        payment.save()
        return redirect("order_payment_failed", payment.order.id)


@login_required
def order_payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "user_side/checkout/payment_failed.html", {"order": order})


@login_required
def retry_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    rp_order = client.order.create({"amount": int(order.total_amount * 100), "currency": "INR"})
    payment, _ = OrderPayment.objects.update_or_create(
        order=order,
        defaults={
            "razorpay_order_id": rp_order["id"],
            "status": "PENDING",
            "razorpay_payment_id": None,
            "razorpay_signature": None,
        }
    )

    return render(request, "user_side/checkout/payment.html", {
"order": order,
"razorpay_order_id": payment.razorpay_order_id,
"razorpay_key": settings.RAZORPAY_KEY_ID,
"razorpay_amount": int(order.total_amount * 100),
})


@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get("code", "").strip()
    cart_items = Cart.objects.select_related("product", "combination").filter(user=request.user)
    cart_items = prepare_checkout_items(cart_items)
    totals = calculate_checkout_totals(cart_items)

    try:
        coupon = validate_and_get_coupon(code, request.user, cart_items, totals["subtotal"])
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)})

    request.session["applied_coupon_id"] = coupon.id
    discount = calculate_coupon_discount(coupon, totals["total"])
    new_total = max(totals["total"] - discount, 0)

    return JsonResponse({
    "success": True,
    "coupon_code": coupon.code,
    "discount_amount": float(discount),
    "new_total": float(new_total),
})


@login_required
@require_POST
def remove_coupon(request):
    request.session.pop("applied_coupon_id", None)
    return JsonResponse({"success": True})