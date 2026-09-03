from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from apps.admin_side.catalog.models import VariantCombination, Product

from .models import Order, OrderItem
from apps.user_side.orders.models import Review

from .services import AdminReturnService

from django.db.models import Q, Sum

from django.contrib import messages


@staff_member_required
def order_list(request):
    orders = Order.objects.select_related('user', 'address')

    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', 'latest')

    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    if status:
        orders = orders.filter(status=status)

    orders = orders.order_by('created_at' if sort == 'oldest' else '-created_at')

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'sort': sort,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin_side/orders/order_list.html', context)


from apps.admin_side.orders.models import Order, OrderItem, OrderPayment   

@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user', 'address').prefetch_related(
            'items',
            'items__product',
            'items__combination',
            'items__combination__variants'
        ),
        id=order_id
    )

    payment = None
    if order.payment_method == "RAZORPAY":
        payment = OrderPayment.objects.filter(order=order).first()

    is_payment_failed = order.payment_method == "RAZORPAY" and payment and payment.status == "FAILED"
    is_payment_pending = order.payment_method == "RAZORPAY" and (not payment or payment.status == "PENDING")

    if order.payment_method == "COD":
        payment_status = "PAID" if order.status == "DELIVERED" else "PENDING"
        
    elif order.payment_method == "RAZORPAY":

        if not payment:
            payment_status = "PENDING"
           
        elif payment.status == "SUCCESS":
            
            payment_status = "PAID"
        
        elif payment.status == "FAILED" :
            payment_status = "FAILED"
        else:
            payment_status = "PENDING"
    elif order.payment_method == "WALLET":
        payment_status = "PAID"
    else:
        payment_status = "PENDING"

    can_update_status = not (is_payment_failed or is_payment_pending)
    
    if request.method == "POST":
        if not can_update_status:
            messages.error(request, "Cannot update order status until payment is completed.")
            return redirect("admin_order_detail", order.id)

        new_status = request.POST.get("status")

        allowed_transitions = {
                    "PENDING": "SHIPPED",
                    "SHIPPED": "OUT_FOR_DELIVERY",
                    "OUT_FOR_DELIVERY": "DELIVERED",
                }

        valid_statuses = [order.status, allowed_transitions.get(order.status)]

        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request, "Order status updated successfully.")
        else:
            messages.error(request, "Invalid status transition.")

        return redirect("admin_order_detail", order.id)

    context = {
                    'order': order,
                    'status_choices': Order.STATUS_CHOICES,
                    'payment': payment,
                    'payment_status': payment_status,
                    'is_payment_failed': is_payment_failed,
                    'is_payment_pending': is_payment_pending,
                    'can_update_status': can_update_status,
                }
    return render(request, 'admin_side/orders/order_detail.html', context)
@staff_member_required
def inventory_list(request):
    search = request.GET.get('search', '').strip()
    stock_filter = request.GET.get('stock', '').strip()

    products = Product.objects.filter(is_active=True).annotate(
        total_stock=Sum('combinations__stock_quantity')   
    )

    if search:
        products = products.filter(Q(name__icontains=search))

    if stock_filter == "out":
        products = products.filter(total_stock=0)
    elif stock_filter == "low":
        products = products.filter(total_stock__gt=0, total_stock__lte=5)
    elif stock_filter == "in":
        products = products.filter(total_stock__gt=5)

    products = products.order_by('name')

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_side/orders/inventory_list.html', {
'page_obj': page_obj,
'search': search,
'stock_filter': stock_filter,
    })


@staff_member_required
def inventory_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    combinations = product.combinations.all().prefetch_related('variants')  

    return render(request, 'admin_side/orders/inventory_detail.html', {
'product': product,
'combinations': combinations,   
})


def update_stock(request, combination_id):  
    combination = get_object_or_404(VariantCombination, id=combination_id)

    if request.method == 'POST':
        stock = request.POST.get('stock')
        combination.stock_quantity = int(stock)
        combination.save()

        messages.success(request, "Stock updated successfully.")
        return redirect('inventory_list')

    return render(request, 'admin_side/orders/update_stock.html', {
    'combination': combination
})


def return_requests(request):
    items = OrderItem.objects.filter(
        status__in=["RETURN_REQUESTED", "RETURNED", "RETURN_REJECTED"]
    ).select_related("product", "order", "order__user")

    paginator = Paginator(items, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "admin_side/orders/return_requests.html", {
"items": items,
'page_obj': page_obj
})


def approve_return(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    AdminReturnService.approve_return(item)
    messages.success(request, "Return approved.")
    return redirect("return_request_detail", item_id=item.id)


def reject_return(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    AdminReturnService.reject_return(item)
    messages.success(request, "Return rejected.")
    return redirect("admin_return_requests")


@staff_member_required
def return_request_detail(request, item_id):
    item = get_object_or_404(
        OrderItem.objects.select_related("order", "order__user", "product", "combination"), 
        id=item_id
    )
    return render(request, "admin_side/orders/return_request_detail.html", {"item": item})


@staff_member_required
def review_list(request):
    reviews = Review.objects.select_related("user", "product").all()
    status = request.GET.get("status")

    if status == "pending":
        reviews = reviews.filter(is_approved=False)
    elif status == "approved":
        reviews = reviews.filter(is_approved=True)

    context = {"reviews": reviews, "status": status}
    return render(request, "admin_side/orders/review_list.html", context)


@staff_member_required
def review_detail(request, review_id):
    review = get_object_or_404(Review.objects.select_related("user", "product"), id=review_id)
    return render(request, "admin_side/orders/review_detail.html", {"review": review})


@staff_member_required
def approve_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = True
    review.save()
    messages.success(request, "Review approved successfully")
    return redirect("admin_reviews")


@staff_member_required
def hide_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_visible = False
    review.save()
    messages.success(request, "Review hidden successfully")
    return redirect("admin_reviews")


@staff_member_required
def unhide_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_visible = True
    review.save()
    messages.success(request, "Review is visible again.")
    return redirect("admin_review_detail", review_id=review.id)


@staff_member_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted successfully")
    return redirect("admin_reviews")

