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
    create_gateway_order,
    prepare_checkout_items,
    calculate_coupon_discount,
    get_available_coupons,
    validate_and_get_coupon,
)
from django.core.cache import cache
from django.contrib.auth import get_user_model
User = get_user_model()
from django.views.decorators.csrf import csrf_exempt
import razorpay
from apps.user_side.accounts.models import Wallet
from apps.admin_side.coupons.models import Coupon, CouponUsage
from django.conf import settings
from apps.admin_side.orders.services import get_current_payable_amount

def _build_buy_now_items(buy_now_data):
    try:
        product = Product.objects.get(
            id=buy_now_data["product_id"],
            is_active=True
        )
        combination_id = buy_now_data["combination_id"]
        quantity = int(buy_now_data["quantity"])
    except (Product.DoesNotExist, KeyError, ValueError):
        return None

    combination = VariantCombination.objects.filter(
        id=combination_id,
        product=product,
        is_active=True
    ).first()

    if not combination:
        return None

    item = BuyNowItem(
        product=product,
        combination=combination,
        quantity=quantity
    )

    return prepare_checkout_items([item])


@login_required
def checkout(request):
    buy_now_data = request.session.get("buy_now")
    is_buy_now = bool(buy_now_data)

    
    if request.method == "POST" and request.POST.get("add_address"):
        is_first_address = not Address.objects.filter(
            user=request.user
        ).exists()

        make_default = bool(request.POST.get("is_primary"))

        if is_first_address and not make_default:
            messages.error(
                request,
                "Please set this as your default address since it's your first one."
            )
            return redirect("checkout")

        if make_default:
            Address.objects.filter(
                user=request.user
            ).update(is_primary=False)

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
        address = Address.objects.get(
                id=request.POST.get("address_id"),
                user=request.user
            )

        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone")
        address.house_no = request.POST.get("address_line_1")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")

        if request.POST.get("is_primary"):
            Address.objects.filter(
                user=request.user
            ).update(is_primary=False)

            address.is_primary = True
        else:
            address.is_primary = False

        address.save()

        return redirect("checkout")

            # -----------------------------
            # GET CHECKOUT ITEMS
            # -----------------------------
    if is_buy_now:
        cart_items = _build_buy_now_items(buy_now_data)

        if not cart_items:
            request.session.pop("buy_now", None)
            messages.error(
                request,
                "That product is no longer available."
            )
            return redirect("shop:product-list")

    else:
        cart_items = (
                Cart.objects
                .select_related("product", "combination")
                .prefetch_related("combination__variants")
                .filter(user=request.user)
            )

        if not cart_items.exists():
            messages.error(
                request,
                "Your cart is empty."
            )
            return redirect("cart:cart")

        cart_items = prepare_checkout_items(cart_items)

                    # -----------------------------
                    # REMOVE OUT-OF-STOCK ITEMS
                    # -----------------------------
    available_items = [
            item
            for item in cart_items
            if item.combination.stock_quantity > 0
        ]

    cart_items = available_items

    if not cart_items:
        if is_buy_now:
            request.session.pop("buy_now", None)
            messages.error(
                request,
                "That product is currently out of stock."
            )
            return redirect("shop:product-list")

        messages.error(
            request,
            "All items in your cart are currently out of stock."
        )
        return redirect("cart:cart")

                        # -----------------------------
                        # CHECKOUT TOTALS
                        # -----------------------------
    addresses = Address.objects.filter(user=request.user)

    default_address = addresses.filter(
        is_primary=True
    ).first()

    wallet, _ = Wallet.objects.get_or_create(
        user=request.user
    )

    totals = calculate_checkout_totals(cart_items)

    available_coupons = get_available_coupons(
        request.user,
        totals["subtotal"]
    )

    coupon_discount = Decimal("0")
    applied_coupon = None

    coupon_id = request.session.get("applied_coupon_id")

    if coupon_id:
        applied_coupon = Coupon.objects.filter(
            id=coupon_id,
            is_active=True,
            is_deleted=False
        ).first()

        if applied_coupon:
            coupon_discount = calculate_coupon_discount(
                applied_coupon,
                totals["total"]
            )

            totals["coupon_discount"] = coupon_discount

            totals["total"] = max(
                totals["total"] - coupon_discount,
                0
            )

                                # -----------------------------
                                # PLACE ORDER
                                # -----------------------------
    if request.method == "POST":
        address_id = request.POST.get("address")

        if not address_id:
            messages.error(
                request,
                "Please select a delivery address."
            )
            return redirect("checkout")

        address = Address.objects.get(
            id=address_id,
            user=request.user
        )

        payment_method = request.POST.get(
            "payment_method",
            "COD"
        )

                                    # Check stock again before creating order
        for item in cart_items:
            if item.combination.stock_quantity < item.quantity:
                messages.error(
                    request,
                    f"Cannot place order. "
                    f"'{item.product.name}' is currently out of stock."
                )

                if is_buy_now:
                    return redirect(
                "shop:product_detail",
                pk=buy_now_data["product_id"]
            )

                return redirect("cart:cart")

        # -----------------------------
        # RAZORPAY: do NOT create an Order yet.
        # Only reserve a gateway order id and stash checkout context
        # in the session. The Order is created later, inside
        # verify_order_payment(), only once Razorpay actually posts
        # back (success or explicit failure). If the user abandons
        # the payment page, nothing here ever runs, so no Order,
        # no OrderItems, no stock reduction, and the cart stays intact.
        # -----------------------------
        if payment_method == "RAZORPAY":
            max_amount = getattr(settings, 'RAZORPAY_MAX_TRANSACTION_AMOUNT', 25000)
            final_total = max(totals["total"] - coupon_discount, 0)

            if final_total > max_amount:
                messages.error(
                    request,
                    "Online payment cannot be processed because the transaction amount exceeds the ₹25,000 limit."
                )
                if is_buy_now:
                    return redirect("shop:product_detail", pk=buy_now_data["product_id"])
                return redirect("cart:cart")

            rp_order_id = create_gateway_order(final_total)

            cache.set(
                f"razorpay_pending:{rp_order_id}",
                {
                    "user_id": request.user.id,
                    "address_id": address.id,
                    "is_buy_now": is_buy_now,
                    "buy_now_data": buy_now_data if is_buy_now else None,
                    "coupon_id": applied_coupon.id if applied_coupon else None,
                    "original_amount": str(totals["original_total"]),
                    "razorpay_order_id": rp_order_id,
                    "amount": str(final_total),
                },
                timeout=1800,
            )
            request.session["razorpay_pending_order_id"] = rp_order_id

            return redirect(reverse("checkout_payment_pending"))
        # -----------------------------
        # COD / WALLET: these complete synchronously right here,
        # so it's safe to create the Order immediately.
        # -----------------------------
        try:
            order = create_order(
                user=request.user,
                address=address,
                cart_items=cart_items,
                payment_method=payment_method,
                coupon_discount=coupon_discount,
                original_amount=totals["original_total"]
            )

            if applied_coupon:
                CouponUsage.objects.create(
                    coupon=applied_coupon,
                    user=request.user,
                    order=order
                )

                request.session.pop(
                    "applied_coupon_id",
                    None
                )

            if is_buy_now:
                request.session.pop(
                    "buy_now",
                    None
                )

        except ValueError as e:
            messages.error(
            request,
            str(e)
        )

            if is_buy_now:
                return redirect(
                                                "shop:product_detail",
            pk=buy_now_data["product_id"]
    )

            return redirect("cart:cart")

        if payment_method == "COD":
            return redirect(reverse("order_success", args=[order.id]))
        elif payment_method == "WALLET":
            return redirect(reverse("order_success", args=[order.id]))
                                            # -----------------------------
                                            # CHECKOUT PAGE
                                            # -----------------------------
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

    return render(
        request,
        "user_side/checkout/checkout.html",
        context
    )
@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
request,
"user_side/checkout/order_success.html",
{"order": order}
)

@login_required
def checkout_payment_pending(request):
    rp_order_id = request.session.get("razorpay_pending_order_id")
    pending = cache.get(f"razorpay_pending:{rp_order_id}") if rp_order_id else None

    if not pending:
        messages.error(request, "Your payment session has expired. Please checkout again.")
        return redirect("checkout")

    return render(request, "user_side/checkout/payment.html", {
        "order": None,
        "display_amount": pending["amount"],
        "razorpay_order_id": pending["razorpay_order_id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_amount": int(Decimal(pending["amount"]) * 100),
    })
@login_required
@require_POST
def set_default_address(request):
    data = json.loads(request.body)

    address_id = data.get("address_id")

    Address.objects.filter(
        user=request.user
    ).update(is_primary=False)

    Address.objects.filter(
        id=address_id,
        user=request.user
    ).update(is_primary=True)

    return JsonResponse({
"success": True
})


@login_required
def checkout_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    max_amount = getattr(settings, 'RAZORPAY_MAX_TRANSACTION_AMOUNT', 25000)
    if order.total_amount > max_amount:
        messages.error(
            request,
            "Online payment cannot be processed because the transaction amount exceeds the ₹25,000 limit."
        )
        return redirect("order_payment_failed", order.id)

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
        "display_amount": order.total_amount,   
})


@csrf_exempt
def verify_order_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")
    razorpay_order_id = request.POST.get("razorpay_order_id")

    if not razorpay_order_id:
        error_metadata_raw = request.POST.get("error[metadata]")
        if error_metadata_raw:
            try:
                error_metadata = json.loads(error_metadata_raw)
            except (ValueError, TypeError):
                error_metadata = {}
            razorpay_order_id = error_metadata.get("order_id")
            if not razorpay_payment_id:
                razorpay_payment_id = error_metadata.get("payment_id")

    if not razorpay_order_id:
        return redirect("checkout")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def _verify():
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })

    # ---- Fresh checkout: no Order exists yet, this is the first attempt ----
    pending = cache.get(f"razorpay_pending:{razorpay_order_id}")
    if pending:
        try:
            user = User.objects.get(id=pending["user_id"])
        except User.DoesNotExist:
            cache.delete(f"razorpay_pending:{razorpay_order_id}")
            return redirect("checkout")

        try:
            address = Address.objects.get(id=pending["address_id"], user=user)
        except Address.DoesNotExist:
            cache.delete(f"razorpay_pending:{razorpay_order_id}")
            return redirect("checkout")

        is_buy_now = pending.get("is_buy_now")
        if is_buy_now:
            buy_now_data = pending.get("buy_now_data")
            cart_items = _build_buy_now_items(buy_now_data) if buy_now_data else None
        else:
            qs = (
                Cart.objects
                .select_related("product", "combination")
                .prefetch_related("combination__variants")
                .filter(user=user)
            )
            cart_items = prepare_checkout_items(qs) if qs.exists() else None

        if not cart_items:
            cache.delete(f"razorpay_pending:{razorpay_order_id}")
            messages.error(request, "Your cart changed before payment completed. Please check out again.")
            return redirect("checkout")

        cart_items = [item for item in cart_items if item.combination.stock_quantity > 0]
        if not cart_items:
            cache.delete(f"razorpay_pending:{razorpay_order_id}")
            messages.error(request, "Items in your order are no longer available.")
            return redirect("checkout")

        applied_coupon = None
        coupon_discount = Decimal("0")
        if pending.get("coupon_id"):
            applied_coupon = Coupon.objects.filter(
                id=pending["coupon_id"], is_active=True, is_deleted=False
            ).first()
            if applied_coupon:
                totals = calculate_checkout_totals(cart_items)
                coupon_discount = calculate_coupon_discount(applied_coupon, totals["total"])

        try:
            _verify()
            payment_status = "SUCCESS"
        except Exception:
            payment_status = "FAILED"

        try:
            order = create_order(
                user=user,
                address=address,
                cart_items=cart_items,
                payment_method="RAZORPAY",
                coupon_discount=coupon_discount,
                original_amount=Decimal(pending["original_amount"]),
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_status=payment_status,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
            )
        except ValueError as e:
            cache.delete(f"razorpay_pending:{razorpay_order_id}")
            messages.error(request, str(e))
            return redirect("cart:cart")

        if applied_coupon:
            CouponUsage.objects.create(coupon=applied_coupon, user=user, order=order)

        cache.delete(f"razorpay_pending:{razorpay_order_id}")
        if request.session.get("razorpay_pending_order_id") == razorpay_order_id:
            request.session.pop("razorpay_pending_order_id", None)
            request.session.pop("applied_coupon_id", None)
            if is_buy_now:
                request.session.pop("buy_now", None)

        if payment_status == "SUCCESS":
            return redirect("order_success", order.id)
        return redirect("order_payment_failed", order.id)

    payment = OrderPayment.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not payment:
        return redirect("checkout")

    try:
        _verify()
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
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
request,
"user_side/checkout/payment_failed.html",
{"order": order}
)

@login_required
def retry_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    payable_amount = get_current_payable_amount(order)

    if order.status == "CANCELLED" or payable_amount <= 0:
        messages.error(request, "This order has nothing pending to pay.")
        return redirect("order_detail", order.id)   # use your actual order-detail URL name here

    max_amount = getattr(settings, 'RAZORPAY_MAX_TRANSACTION_AMOUNT', 25000)

    if payable_amount > max_amount:
        messages.error(
            request,
            "Online payment cannot be processed because the transaction amount exceeds the ₹25,000 limit."
        )
        return redirect("order_payment_failed", order.id)

    rp_order_id = create_gateway_order(payable_amount)

    payment = OrderPayment.objects.filter(order=order).first()
    if payment:
        payment.razorpay_order_id = rp_order_id
        payment.razorpay_payment_id = None
        payment.razorpay_signature = None
        payment.save(update_fields=["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"])
    else:
        payment = OrderPayment.objects.create(order=order, razorpay_order_id=rp_order_id, status="FAILED")

    return render(request, "user_side/checkout/payment.html", {
        "order": order,
        "razorpay_order_id": payment.razorpay_order_id,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_amount": int(payable_amount * 100),
        "display_amount": payable_amount,   
         "display_amount": payable_amount, # NEW

    })
@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get(
        "code",
        ""
    ).strip()

    # Check whether this is a Buy Now checkout
    buy_now_data = request.session.get("buy_now")
    is_buy_now = bool(buy_now_data)

    # Get the same checkout items used by checkout page
    if is_buy_now:
        cart_items = _build_buy_now_items(
            buy_now_data
        )

        if not cart_items:
            return JsonResponse({
        "success": False,
        "error": "That product is no longer available."
    })

    else:
        cart_items = (
            Cart.objects
            .select_related("product", "combination")
            .prefetch_related("combination__variants")
            .filter(user=request.user)
        )

        if not cart_items.exists():
            return JsonResponse({
        "success": False,
        "error": "Your cart is empty."
    })

    cart_items = prepare_checkout_items(
        cart_items
    )

        # Use only items that still have stock
    cart_items = [
        item
        for item in cart_items
        if item.combination.stock_quantity > 0
    ]

    if not cart_items:
        return JsonResponse({
    "success": False,
    "error": "No available items to apply the coupon."
})

    totals = calculate_checkout_totals(
        cart_items
    )

    print(
        "COUPON CHECK SUBTOTAL:",
        totals["subtotal"]
    )

    print(
        "COUPON CHECK TOTAL:",
        totals["total"]
    )

    try:
        coupon = validate_and_get_coupon(
            code,
            request.user,
            cart_items,
            totals["subtotal"]
        )

    except ValueError as e:
        return JsonResponse({
    "success": False,
    "error": str(e)
})

    request.session["applied_coupon_id"] = coupon.id

    discount = calculate_coupon_discount(
        coupon,
        totals["total"]
    )

    new_total = max(
        totals["total"] - discount,
        0
    )

    return JsonResponse({
        "success": True,
        "coupon_code": coupon.code,
        "discount_amount": float(discount),
        "new_total": float(new_total),
    })


@login_required
@require_POST
def remove_coupon(request):
    request.session.pop(
        "applied_coupon_id",
        None
    )

    return JsonResponse({
"success": True
})
