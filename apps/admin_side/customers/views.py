from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum

from django.views.decorators.cache import never_cache
from .forms import UserFilterForm



from apps.admin_side.orders.models import Order  
from apps.user_side.shop.models import Wishlist
from apps.user_side.orders.models import Review


@never_cache
@staff_member_required
def user_management_view(request):
    user_list = User.objects.filter(is_staff=False).annotate(
        order_count=Count('orders')
    ).order_by('-date_joined')

    form = UserFilterForm(request.GET)
    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        status_filter = form.cleaned_data.get('status')
        sort_filter = form.cleaned_data.get('sort')

        if search_query:
            user_list = user_list.filter(
                Q(first_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(username__icontains=search_query)
            )
        if status_filter == 'active':
            user_list = user_list.filter(is_active=True)
        elif status_filter == 'blocked':
            user_list = user_list.filter(is_active=False)

                
        if sort_filter == 'new':
            user_list = user_list.order_by('-date_joined')
        elif sort_filter == 'old':
            user_list = user_list.order_by('date_joined')

    paginator = Paginator(user_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'admin_side/customers/user_management.html', {'users': page_obj})

    return render(request, 'admin_side/customers/user_management.html', {
            'users': page_obj,
            'form': form,
            'current_status': request.GET.get('status', ''),
            'current_sort': request.GET.get('sort', ''),
        })


@never_cache
@staff_member_required
def user_detail_view(request, user_id):
    customer = get_object_or_404(User, id=user_id)

    profile = getattr(customer, 'profile', None)

    primary_address = customer.addresses.filter(is_primary=True).first() or customer.addresses.first()

    orders = customer.orders.all().order_by('-created_at')[:5]
    total_orders = customer.orders.count()
    total_spent = customer.orders.exclude(status='CANCELLED').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    wishlist_items = Wishlist.objects.filter(user=customer).select_related('product', 'combination')[:1]
    reviews = Review.objects.filter(user=customer).select_related('product')[:2]

    return render(request, 'admin_side/customers/user_detail.html', {
            'customer': customer,
            'profile': profile,
            'primary_address': primary_address,
            'orders': orders,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'wishlist_items': wishlist_items,
            'reviews': reviews,
        })


@staff_member_required
def toggle_user_status(request, user_id):
    if request.method == "POST":
        customer = get_object_or_404(User, id=user_id)
        customer.is_active = not customer.is_active
        customer.save()
        messages.success(request, f"Status for {customer.username} updated.")
    return redirect('user-management')