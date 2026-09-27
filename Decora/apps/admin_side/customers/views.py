from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q ,Count
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
from .forms import UserFilterForm
from django.db.models import Sum
from apps.user_side.shop.models import Wishlist   
from apps.user_side.orders.models import Review    
from django.utils.http import url_has_allowed_host_and_scheme


@never_cache
@staff_member_required
def user_management_view(request):
    user_list = User.objects.filter(is_staff=False).annotate(
        order_count=Count('orders', distinct=True)   # confirm related_name
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
    page_obj = paginator.get_page(request.GET.get('page'))

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

    orders = customer.orders.all().order_by('-created_at')
    total_orders = orders.count()
    total_spent = customer.orders.exclude(status='CANCELLED').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    wishlist_items = Wishlist.objects.filter(user=customer).select_related('product', 'combination')
    addresses = customer.addresses.all()
    reviews = Review.objects.filter(user=customer).select_related('product')

    return render(request, 'admin_side/customers/user_detail.html', {
'customer': customer,
'profile': profile,
'primary_address': primary_address,
'orders': orders,
'total_orders': total_orders,
'total_spent': total_spent,
'wishlist_items': wishlist_items,
'addresses': addresses,
'reviews': reviews,
})

@staff_member_required
def toggle_user_status(request, user_id):
    customer = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        customer.is_active = not customer.is_active
        customer.save()
        status_word = "blocked" if not customer.is_active else "unblocked"
        messages.success(request, f"{customer.username} has been {status_word}.")

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('user-management')