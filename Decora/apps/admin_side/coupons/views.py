import random
import string

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Coupon


def admin_required(view):
    return user_passes_test(lambda u: u.is_staff)(view)


def _generate_unique_code(prefix="DECORA", length=6):
    chars = string.ascii_uppercase + string.digits
    for _ in range(20):
        suffix = ''.join(random.choices(chars, k=length))
        code = f"{prefix}-{suffix}" if prefix else suffix
        if not Coupon.objects.filter(code=code, is_deleted=False).exists():
            return code
        return f"{prefix}-{random.randint(100000, 999999)}"


@admin_required
def coupon_generate_code(request):
    code = _generate_unique_code()
    return JsonResponse({'code': code})


@admin_required
def coupon_list(request):
    coupons = Coupon.objects.filter(is_deleted=False).order_by('-created_at')
    return render(request, 'admin_side/coupons/coupon_list.html', {'coupons': coupons})


def _parse_and_save_coupon(request, coupon=None):
    """Shared logic for create + edit. Returns (success: bool, redirect_name: str)."""
    code = request.POST.get("code", "").strip().upper()
    discount_type = request.POST.get("discount_type", "flat")

    if discount_type not in ("flat", "percentage"):
        discount_type = "flat"

    duplicate_qs = Coupon.objects.filter(code=code, is_deleted=False)
    if coupon:
        duplicate_qs = duplicate_qs.exclude(id=coupon.id)

    if duplicate_qs.exists():
        messages.error(request, "Coupon code already exists.")
        return False

    discount_amount = request.POST.get("discount_amount")
    max_discount_amount = request.POST.get("max_discount_amount") or None
    min_order_value = request.POST.get("min_order_value") or 0
    valid_from = request.POST.get("valid_from")
    valid_until = request.POST.get("valid_until")

    if not code or not discount_amount or not valid_from or not valid_until:
        messages.error(request, "All required fields must be filled.")
        return False
    try:
        discount_amount = float(discount_amount)
        if discount_amount <= 0:
            raise ValueError
        if discount_type == "percentage" and discount_amount > 100:
            messages.error(request, "Percentage discount cannot exceed 100.")
            return False
    except ValueError:
        messages.error(request, "Discount amount must be a positive number.")
        return False

    if max_discount_amount is not None:
        try:
            max_discount_amount = float(max_discount_amount)
            if max_discount_amount <= 0:
                max_discount_amount = None
        except ValueError:
            max_discount_amount = None

    if discount_type == "flat":
        max_discount_amount = None

    fields = dict(
        code=code,
        discount_type=discount_type,
        discount_amount=discount_amount,
        max_discount_amount=max_discount_amount,
        min_order_value=min_order_value,
        valid_from=valid_from,
        valid_until=valid_until,
        usage_limit_per_user=request.POST.get("usage_limit_per_user") or None,
        total_usage_limit=request.POST.get("total_usage_limit") or None,
    )

    if coupon:
        for key, value in fields.items():
            setattr(coupon, key, value)
            coupon.save()
    else:
        Coupon.objects.create(**fields)

    return True


@admin_required
def coupon_create(request):
    if request.method == "POST":
        if _parse_and_save_coupon(request):
            messages.success(request, "Coupon created successfully.")
            return redirect("coupon_list")
        return redirect("coupon_create")

    return render(request, 'admin_side/coupons/coupon_form.html')


@admin_required
def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id, is_deleted=False)

    if request.method == "POST":
        if _parse_and_save_coupon(request, coupon=coupon):
            messages.success(request, "Coupon updated successfully.")
            return redirect("coupon_list")
        return redirect("coupon_edit", coupon_id=coupon.id)

    return render(request, 'admin_side/coupons/coupon_form.html', {'coupon': coupon})


@admin_required
def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_deleted = True
    coupon.is_active = False
    coupon.save()
    messages.success(request, "Coupon deleted.")
    return redirect("coupon_list")


@admin_required
@require_POST
def coupon_toggle_active(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id, is_deleted=False)
    coupon.is_active = not coupon.is_active
    coupon.save()
    status = "activated" if coupon.is_active else "deactivated"
    messages.success(request, f"Coupon {coupon.code} {status}.")
    return redirect("coupon_list")