from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from itertools import chain
from .models import ProductOffer, CategoryOffer, ReferralOffer
from apps.admin_side.catalog.models import Product, Category
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.paginator import Paginator
from django.db.models import Q

def _parse_local_datetime(raw_value):
    naive_dt = parse_datetime(raw_value)
    if naive_dt is None:
        return None
    if timezone.is_naive(naive_dt):
        naive_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
    return naive_dt

def admin_required(view):
    return user_passes_test(lambda u: u.is_staff)(view)

@admin_required
def offer_list(request):
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')

    product_offers = ProductOffer.objects.select_related('product').order_by('-created_at')
    category_offers = CategoryOffer.objects.select_related('category').order_by('-created_at')

    if search:
        product_offers = product_offers.filter(
            Q(name__icontains=search) | Q(product__name__icontains=search)
        )
        category_offers = category_offers.filter(
            Q(name__icontains=search) | Q(category__name__icontains=search)
        )

    if status == 'active':
        product_offers = product_offers.filter(is_active=True)
        category_offers = category_offers.filter(is_active=True)
    elif status == 'inactive':
        product_offers = product_offers.filter(is_active=False)
        category_offers = category_offers.filter(is_active=False)

    for o in product_offers:
        o.offer_kind = 'product'
        o.target_name = o.product.name
    for o in category_offers:
        o.offer_kind = 'category'
        o.target_name = o.category.name

    offers = sorted(
        chain(product_offers, category_offers),
        key=lambda o: o.created_at,
        reverse=True
    )

    paginator = Paginator(offers, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_side/offers/offer_list.html', {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    })

def _offer_form_context(products, categories, offer=None):
    return {'products': products, 'categories': categories, 'offer': offer}

@admin_required
def offer_create(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)

    if request.method == "POST":
        offer_type = request.POST.get("offer_type")
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        discount_type = request.POST.get("discount_type", "percent")
        discount_value = request.POST.get("discount_percent")
        is_active = request.POST.get("is_active") == "on"
        valid_from = _parse_local_datetime(request.POST.get("valid_from"))
        valid_until = _parse_local_datetime(request.POST.get("valid_until"))

        if offer_type not in ("product", "category"):
            messages.error(request, "Invalid offer type.")
            return redirect("offer_create")
        if not name:
            messages.error(request, "Offer name is required.")
            return redirect("offer_create")
        if not discount_value or not valid_from or not valid_until:
            messages.error(request, "All required fields must be filled.")
            return redirect("offer_create")

        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                raise ValueError
            if discount_type == "percent" and discount_value > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "Enter a valid discount value.")
            return redirect("offer_create")

        if offer_type == "product":
            product_id = request.POST.get("product")
            if not product_id:
                messages.error(request, "Please select a product.")
                return redirect("offer_create")
            product = get_object_or_404(Product, id=product_id)
            ProductOffer.objects.create(
                name=name, description=description, discount_type=discount_type,
                product=product, discount_percent=discount_value,
                valid_from=valid_from, valid_until=valid_until, is_active=is_active,
            )
        else:
            category_id = request.POST.get("category")
            if not category_id:
                messages.error(request, "Please select a category.")
                return redirect("offer_create")
            category = get_object_or_404(Category, id=category_id)
            CategoryOffer.objects.create(
                    name=name, description=description, discount_type=discount_type,
                    category=category, discount_percent=discount_value,
                    valid_from=valid_from, valid_until=valid_until, is_active=is_active,
                )

        messages.success(request, "Offer created successfully.")
        return redirect("offer_list")

    return render(request, 'admin_side/offers/offer_form.html',_offer_form_context(products, categories))

@admin_required
def offer_edit(request, offer_type, offer_id):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)

    model = ProductOffer if offer_type == "product" else CategoryOffer
    offer = get_object_or_404(model, id=offer_id)
    offer.offer_kind = offer_type  

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        discount_type = request.POST.get("discount_type", "percent")
        discount_value = request.POST.get("discount_percent")
        is_active = request.POST.get("is_active") == "on"
        valid_from = _parse_local_datetime(request.POST.get("valid_from"))
        valid_until = _parse_local_datetime(request.POST.get("valid_until"))

        if not name or not discount_value or not valid_from or not valid_until:
            messages.error(request, "All required fields must be filled.")
            return redirect("offer_edit", offer_type=offer_type, offer_id=offer_id)

        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                raise ValueError
            if discount_type == "percent" and discount_value > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "Enter a valid discount value.")
            return redirect("offer_edit", offer_type=offer_type, offer_id=offer_id)

        if offer_type == "product":
            product_id = request.POST.get("product")
            offer.product = get_object_or_404(Product, id=product_id)
        else:
            category_id = request.POST.get("category")
            offer.category = get_object_or_404(Category, id=category_id)

        offer.name = name
        offer.description = description
        offer.discount_type = discount_type
        offer.discount_percent = discount_value
        offer.valid_from = valid_from
        offer.valid_until = valid_until
        offer.is_active = is_active
        offer.save()

        messages.success(request, "Offer updated successfully.")
        return redirect("offer_list")

    return render(request, 'admin_side/offers/offer_form.html',_offer_form_context(products, categories, offer=offer))

@admin_required
def offer_delete(request, offer_type, offer_id):
    if offer_type == "product":
        offer = get_object_or_404(ProductOffer, id=offer_id)
    elif offer_type == "category":
        offer = get_object_or_404(CategoryOffer, id=offer_id)
    else:
        messages.error(request, "Invalid offer type.")
        return redirect("offer_list")

    offer.delete()
    messages.success(request, "Offer deleted.")
    return redirect("offer_list")


@admin_required
def referral_offer_list(request):
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')

    referrals = ReferralOffer.objects.select_related(
        'referrer', 'referred_user'
    ).order_by('-created_at')

    if search:
        referrals = referrals.filter(
            Q(referral_code__icontains=search) |
            Q(referrer__first_name__icontains=search) |
            Q(referrer__email__icontains=search) |
            Q(referred_user__first_name__icontains=search) |
            Q(referred_user__email__icontains=search)
        )

    if status == 'used':
        referrals = referrals.filter(is_used=True)
    elif status == 'unused':
        referrals = referrals.filter(is_used=False)

    paginator = Paginator(referrals, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_side/offers/referral_offer_list.html', {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    })
