import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart
from apps.admin_side.catalog.models import Product, VariantCombination
from apps.core.utils import get_combination_pricing




@login_required
def cart_view(request):
    cart_items = (
        Cart.objects.filter(user=request.user)
        .select_related('product', 'product__category', 'combination')
        .prefetch_related('combination__variants')
        .order_by('-created_at')
    )

    subtotal = 0
    original_total = 0

    for item in cart_items:
        combo = item.combination
        color_variant = combo.variants.filter(variant_type='Color').first()

        item.image_variant = color_variant
        item.variant_display = " / ".join(
            v.variant_value.upper() for v in combo.variants.all()
        )
        item.stock_limit = combo.stock_quantity
        item.is_out_of_stock = combo.is_out_of_stock

        pricing = get_combination_pricing(combo)
        item.final_price = pricing["final_price"]
        item.original_price = pricing["original_price"]
        item.item_total = item.final_price * item.quantity
        item.original_item_total = item.original_price * item.quantity

        subtotal += item.item_total
        original_total += item.original_item_total

    saved_amount = original_total - subtotal
    available_items_count = sum(1 for item in cart_items if not item.is_out_of_stock)
    all_items_out_of_stock = cart_items.exists() and available_items_count == 0

    return render(request, 'user_side/cart/cart.html', {
    'cart_items': cart_items,
    'subtotal': subtotal,
    'original_total': original_total,
    'saved_amount': saved_amount,
    'shipping': 0,
    'total': subtotal,
    'all_items_out_of_stock': all_items_out_of_stock,
})


@login_required
def add_to_cart(request, product_id):
    data = json.loads(request.body)
    combination_id = data.get('combination_id')
    quantity = int(data.get('quantity', 1))

    product = get_object_or_404(Product, id=product_id)

    if not combination_id:
        return JsonResponse({'status': 'error', 'message': 'No combination selected'})

    combination = VariantCombination.objects.filter(
        id=combination_id, product=product, is_active=True
    ).first()

    if not combination:
        return JsonResponse({'status': 'error', 'message': 'Combination not found'})

    if combination.stock_quantity <= 0:
        return JsonResponse({
    'status': 'out_of_stock',
    'message': 'Cannot add to cart because this product is out of stock.'
})

    quantity = min(quantity, combination.stock_quantity, 5)

    cart_item = Cart.objects.filter(user=request.user, combination=combination).first()

    if cart_item:
        if cart_item.quantity >= 5:
            return JsonResponse({'status': 'limit_reached', 'message': 'You can only add 5 items'})

        if cart_item.quantity >= combination.stock_quantity:
            return JsonResponse({
        'status': 'stock_reached',
        'message': f'Cannot add to cart. Only {combination.stock_quantity} item(s) available in stock.'
    })

        cart_item.quantity = min(cart_item.quantity + quantity, combination.stock_quantity, 5)
        cart_item.save()

        cart_count = Cart.objects.filter(user=request.user).count()
        return JsonResponse({
            'status': 'updated',
            'quantity': cart_item.quantity,
            'cart_count': cart_count,
            'message': f'{product.name} quantity updated'
        })

    cart_item = Cart.objects.create(
        user=request.user,
        product=product,
        combination=combination,
        quantity=quantity
    )
    cart_count = Cart.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': 'added',
        'quantity': cart_item.quantity,
        'cart_count': cart_count,
        'message': f'{product.name} added to cart'
    })

@login_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('cart:cart')


@login_required
def update_cart_quantity(request, cart_id):
    data = json.loads(request.body)
    action = data.get('action')

    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    combo = cart_item.combination

    if action == 'increase':
        if cart_item.quantity >= 5:
            return JsonResponse({'status': 'limit_reached', 'message': 'You can only add 5 items'})

        if cart_item.quantity >= combo.stock_quantity:
            return JsonResponse({
        'status': 'stock_reached',
        'message': f'Only {combo.stock_quantity} item(s) available in stock'
    })

        cart_item.quantity += 1

    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1

    cart_item.save()

    pricing = get_combination_pricing(combo)
    item_total = pricing['final_price'] * cart_item.quantity

    subtotal = 0
    cart_items = Cart.objects.filter(user=request.user).select_related('combination')
    for item in cart_items:
        p = get_combination_pricing(item.combination)
        subtotal += p['final_price'] * item.quantity

    return JsonResponse({
                'status': 'success',
                'quantity': cart_item.quantity,
                'item_total': item_total,
                'subtotal': subtotal,
                'total': subtotal
            })