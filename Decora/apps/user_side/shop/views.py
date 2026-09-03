import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.db.models import Q, Min, OuterRef, Subquery
from django.core.paginator import Paginator
from django.utils import timezone

from apps.core.utils import (
    get_best_offer_discount_amount,
    get_best_offer_display,
    get_combination_pricing,
    get_product_rating_stats,
)
from apps.admin_side.catalog.models import Category, Product, Room, VariantCombination
from apps.admin_side.offers.models import CategoryOffer
from apps.user_side.cart.models import Cart
from apps.user_side.orders.models import Review
from .models import Wishlist



@never_cache
@login_required(login_url='user_login')
def home_view(request):
    active_categories = Category.objects.filter(is_active=True)
    now = timezone.now()

    for cat in active_categories:
        offer = CategoryOffer.objects.filter(
            category=cat, is_active=True,
            valid_from__lte=now, valid_until__gte=now
        ).order_by('-discount_percent').first()
        if offer:
            cat.active_offer_label = f"₹{int(offer.discount_percent)} OFF" if offer.discount_type == "fixed" else f"{int(offer.discount_percent)}% OFF"
        else:
            cat.active_offer_label = None

    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True,
        combinations__is_active=True
    ).distinct()[:8]

    for product in featured_products:
        combo = product.default_combination

        if not combo:
            product.featured_image_variant = None
            product.featured_combination_id = None
            product.featured_original_price = 0
            product.featured_final_price = 0
            product.featured_has_discount = False
            product.featured_offer_label = None
            continue

        pricing = get_combination_pricing(combo)
        color_variant = combo.variants.filter(variant_type='Color').first()

        product.featured_image_variant = color_variant
        product.featured_combination_id = combo.id
        product.featured_original_price = float(pricing["original_price"])
        product.featured_final_price = float(pricing["final_price"])
        product.featured_has_discount = (pricing["combo_discount"] + pricing["offer_discount"]) > 0
        product.featured_offer_label, _ = get_best_offer_display(product)

    return render(request, 'user_side/shop/home.html', {
                'categories': active_categories,
                'featured_products': featured_products,
            })


from django.db.models import OuterRef, Subquery

def product_list(request):
    category_names = request.GET.getlist('category')
    room_names = request.GET.getlist('room')
    sort_option = request.GET.get('sort', 'newest')   
    search_query = request.GET.get('search', '').strip()
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')

    qs = Product.objects.filter(is_active=True, combinations__is_active=True)

    if category_names:
        qs = qs.filter(category__name__in=category_names)
    if room_names:
        qs = qs.filter(room__name__in=room_names)
    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(room__name__icontains=search_query)
            )

    qs = qs.distinct().prefetch_related('combinations')

    try:
        min_price = Decimal(min_price_param) if min_price_param not in (None, '') else Decimal('0')
    except Exception:
        min_price = Decimal('0')
    try:
        max_price = Decimal(max_price_param) if max_price_param not in (None, '') else Decimal('50000')
    except Exception:
        max_price = Decimal('50000')

    enriched = []
    for product in qs:
        product.offer_label, _ = get_best_offer_display(product)
        product.avg_rating, product.review_count = get_product_rating_stats(product)
        active_combos = list(product.combinations.filter(is_active=True))
        if not active_combos:
            continue

        priced_combos = [(c, get_combination_pricing(c)) for c in active_combos]
        cheapest_combo, cheapest_pricing = min(
            priced_combos, key=lambda pair: pair[1]["final_price"]
        )

                            
        display_price = float(cheapest_pricing["final_price"])

        if display_price < float(min_price) or display_price > float(max_price):
            continue

        default_combo = product.default_combination or cheapest_combo
        default_pricing = next(
            (p for c, p in priced_combos if c.id == default_combo.id),
            cheapest_pricing
        )

        product.shop_image = default_combo.main_image if default_combo.main_image else cheapest_combo.main_image
        product.shop_combination_id = default_combo.id
        product.original_price = float(default_pricing["original_price"])
        product.final_price = float(default_pricing["final_price"])
        product.min_display_price = display_price
        product.total_discount = default_pricing["combo_discount"] + default_pricing["offer_discount"]
        offer_label, _ = get_best_offer_display(product)

        if request.user.is_authenticated:
            product.is_in_wishlist = Wishlist.objects.filter(
                user=request.user, product=product, combination=default_combo
            ).exists()
        else:
            product.is_in_wishlist = False

        enriched.append(product)

    if sort_option == 'featured':
        enriched = [p for p in enriched if p.is_featured]
        enriched.sort(key=lambda p: p.created_at, reverse=True)
    elif sort_option == 'oldest':
        enriched.sort(key=lambda p: p.created_at)
    elif sort_option == 'price_low':
        enriched.sort(key=lambda p: p.min_display_price)
    elif sort_option == 'price_high':
        enriched.sort(key=lambda p: p.min_display_price, reverse=True)
    elif sort_option == 'name_az':
        enriched.sort(key=lambda p: p.name.lower())
    elif sort_option == 'name_za':
        enriched.sort(key=lambda p: p.name.lower(), reverse=True)
        enriched.sort(key=lambda p: p.created_at, reverse=True)

    paginator = Paginator(enriched, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    products = page_obj

    querydict = request.GET.copy()
    if 'page' in querydict:
        querydict.pop('page')

    categories = Category.objects.filter(is_active=True)
    rooms = Room.objects.filter(is_active=True)

    context = {
                'products': products,
                'categories': categories,
                'rooms': rooms,
                'querystring': querydict.urlencode(),
                'selected_categories': category_names,
                'selected_rooms': room_names,
                'current_sort': sort_option,
                'min_price': int(min_price),
                'max_price': int(max_price),
                'search_query': search_query,
            }
    return render(request, 'user_side/shop/shop.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.filter(is_active=True), pk=pk)
    avg_rating, review_count = get_product_rating_stats(product)

    combinations = list(
        product.combinations
        .filter(is_active=True)
        .prefetch_related('variants', 'gallery')
    )

    variant_groups_raw = {}
    for combo in combinations:
        for v in combo.variants.all():
            variant_groups_raw.setdefault(v.variant_type, {})[v.id] = v

    variant_groups = {
        group_name: list(values.values())
        for group_name, values in variant_groups_raw.items()
    }

    combo_lookup = {}
    for combo in combinations:
        variant_ids = sorted(combo.variants.values_list('id', flat=True))
        key = ",".join(str(i) for i in variant_ids)

        pricing = get_combination_pricing(combo)

        gallery_urls = [img.image.url for img in combo.gallery.all()]

        combo_lookup[key] = {
            "combination_id": combo.id,
            "sku": combo.sku or "",
            "stock": combo.stock_quantity,
            "is_out_of_stock": combo.is_out_of_stock,
            "original_price": float(pricing["original_price"]),
            "final_price": float(pricing["final_price"]),
            "has_discount": (pricing["combo_discount"] + pricing["offer_discount"]) > 0,
            "image": combo.main_image.url if combo.main_image else "",
            "gallery": gallery_urls,
            "variant_ids": variant_ids,
        }

    default_combination = product.default_combination
    default_key = None
    if default_combination:
        default_ids = sorted(default_combination.variants.values_list('id', flat=True))
        default_key = ",".join(str(i) for i in default_ids)

    default_combo_data = combo_lookup.get(default_key) if default_key else None
    default_color_variant = (
        default_combination.variants.filter(variant_type='Color').first()
        if default_combination else None
    )

    any_in_stock = any(c.stock_quantity > 0 for c in combinations)
    reviews = (
    Review.objects
    .filter(product=product, is_approved=True, is_visible=True)
    .select_related('user')
    .order_by('-created_at')
)
    offer_label, _ = get_best_offer_display(product)
    related_products = (
    Product.objects.filter(
        category=product.category,
        is_active=True,
        combinations__is_active=True,
    )
    .exclude(id=product.id)
    .distinct()[:4]
)

    wishlist_combination_ids = []
    if request.user.is_authenticated:
        wishlist_combination_ids = list(
            Wishlist.objects.filter(user=request.user, product=product)
            .values_list('combination_id', flat=True)
            )

    

    context = {
    'product': product,
    'variant_groups': variant_groups,
    'combo_lookup_json': json.dumps(combo_lookup),
    'default_combination': default_combination,
    'default_combo_data': default_combo_data,
    'default_color_variant': default_color_variant,
    'default_key': default_key,
    'any_in_stock': any_in_stock,
    'related_products': related_products,
    'offer_label': offer_label,  
'wishlist_combination_ids': json.dumps(wishlist_combination_ids),
    'avg_rating': avg_rating,
    'review_count': review_count,
    'reviews': reviews,
}
    return render(request, 'user_side/shop/product_detail.html', context)


@login_required
def buy_now(request, product_id):
    if request.method != "POST":
        return redirect("shop:product_detail", pk=product_id)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {}

    combination_id = data.get("combination_id")
    quantity = int(data.get("quantity", 1))

    product = get_object_or_404(Product, id=product_id)

    if not combination_id:
        return JsonResponse({"status": "error", "message": "No combination selected"})

    combination = VariantCombination.objects.filter(
            id=combination_id, product=product, is_active=True
        ).first()

    if not combination:
        return JsonResponse({"status": "error", "message": "Combination not found"})

    if combination.stock_quantity <= 0:
        return JsonResponse({"status": "out_of_stock", "message": "This item is out of stock."})

    quantity = min(quantity, combination.stock_quantity, 5)

    request.session["buy_now"] = {
        "product_id": product_id,
        "combination_id": combination.id,
        "quantity": quantity,
    }

    return JsonResponse({"status": "ok", "redirect": "/checkout/"})


@login_required
def wishlist_view(request):
    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related('product', 'product__category', 'combination')
        .prefetch_related('combination__variants')
        .order_by('-created_at')
    )

    for item in wishlist_items:
        pricing = get_combination_pricing(item.combination)
        item.original_price = pricing["original_price"]
        item.total_discount = pricing["combo_discount"] + pricing["offer_discount"]
        item.total_price = pricing["final_price"]
        item.stock_limit = item.combination.stock_quantity

    return render(request, 'user_side/shop/wishlist.html', {
    'wishlist_items': wishlist_items
})


@login_required
def toggle_wishlist(request, product_id):
    data = json.loads(request.body)
    combination_id = data.get("combination_id")

    product = get_object_or_404(Product, id=product_id)
    combination = get_object_or_404(VariantCombination, id=combination_id, product=product)

    existing = Wishlist.objects.filter(
        user=request.user, product=product, combination=combination
    ).first()

    if existing:
        existing.delete()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({"status": "removed", "wishlist_count": wishlist_count})

    Wishlist.objects.create(user=request.user, product=product, combination=combination)
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({"status": "added", "wishlist_count": wishlist_count})


@login_required
def remove_from_wishlist(request, product_id):
    combination_id = request.GET.get('combination')

    if combination_id:
        Wishlist.objects.filter(
            user=request.user, product_id=product_id, combination_id=combination_id
        ).delete()

    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'status': 'success', 'wishlist_count': wishlist_count})


@login_required
def add_wishlist_to_cart(request, product_id):
    try:
        data = json.loads(request.body)
    except Exception:
        data = {}

    combination_id = data.get('combination_id')

    product = get_object_or_404(Product, id=product_id)
    combination = get_object_or_404(VariantCombination, id=combination_id, product=product)

    if combination.stock_quantity <= 0:
        return JsonResponse({
        'status': 'out_of_stock',
        'message': 'Cannot move to cart. This product is currently out of stock.'
    })

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        combination=combination,
        defaults={'product': product, 'quantity': 1}
    )

    if not created:
        if cart_item.quantity >= combination.stock_quantity or cart_item.quantity >= 5:
            return JsonResponse({
        'status': 'stock_reached',
        'message': f'Only {combination.stock_quantity} item(s) available in stock.'
    })
        cart_item.quantity += 1
        cart_item.save()

    Wishlist.objects.filter(
        user=request.user, product=product, combination=combination
    ).delete()

    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    cart_count = Cart.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': 'success',
        'message': f'{product.name} added to cart',
        'created': created,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
    })


@login_required
def combination_wishlist_status(request, product_id, combination_id):
    exists = Wishlist.objects.filter(
        user=request.user, product_id=product_id, combination_id=combination_id
    ).exists()
    return JsonResponse({"is_in_wishlist": exists})