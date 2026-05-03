from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import resolve_url
from django.db.models import Q 
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
# Create a custom decorator that actually respects your URL names

def admin_login_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        user = authenticate(request, username=u, password=p)
        
        if user is not None and user.is_staff:
            login(request,    user)
            return redirect('admin-dashboard') 
        else:
            messages.error(request, "Invalid Admin Credentials")
            return redirect('admin-login')
            
    return render(request, 'admin/login.html')
@staff_member_required # Ensures only admins can see this
# admin/views.py

def admin_dashboard_view(request):
    stats = [
        {'title': 'Total Orders', 'value': '1,284', 'growth': '+12%', 'icon': 'bag-shopping'},
        {'title': 'Total Revenue', 'value': '$48,520', 'growth': '+8.4%', 'icon': 'wallet'},
        {'title': 'Total Users', 'value': '8,902', 'growth': '+5%', 'icon': 'user-plus'},
        {'title': 'Total Products', 'value': '452', 'growth': 'Active', 'icon': 'clipboard-check'},
    ]

    # Create the sidebar list here
    
    return render(request, 'admin/dashboard.html', {
        'stats': stats,
         # Pass it to the template
    })

# Placeholder for user management

def logout_view(request): # Rename your function to be safe
    auth_logout(request)  # Call the aliased Django function
    return redirect('login')

@never_cache
@staff_member_required
def user_management_view(request):
    user_list = User.objects.filter(is_staff=False).order_by('-date_joined')

    # --- Search Logic ---
    search_query = request.GET.get('search', '')
    if search_query:
        user_list = user_list.filter(
            Q(first_name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )

    # --- Filtering Logic ---
    status_filter = request.GET.get('status')
    sort_filter = request.GET.get('sort')

    if status_filter == 'active':
        user_list = user_list.filter(is_active=True)
    elif status_filter == 'blocked':
        user_list = user_list.filter(is_active=False)

    if sort_filter == 'new':
        seven_days_ago = timezone.now() - timedelta(days=7)
        user_list = user_list.filter(date_joined__gte=seven_days_ago)
    elif sort_filter == 'old':
        user_list = user_list.order_by('date_joined')

    # --- Pagination ---
    paginator = Paginator(user_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/user_management.html', {
        'users': page_obj,
        'current_status': status_filter,
        'current_sort': sort_filter,
        'search_query': search_query # Pass this back to the template
    })
@never_cache
@staff_member_required
def user_detail_view(request, user_id):
    # Fetch the specific user or 404 if they don't exist
    customer = get_object_or_404(User, id=user_id)
    
    # If you have an Order model, you can fetch their history here
    # order_history = customer.order_set.all().order_by('-created_at')
    
    return render(request, 'admin/user_detail.html', {
        'customer': customer,
        # 'orders': order_history,
    })

@staff_member_required
def toggle_user_status(request, user_id):
    if request.method == "POST":
        customer = get_object_or_404(User, id=user_id)
        customer.is_active = not customer.is_active
        customer.save()
        messages.success(request, f"Status for {customer.username} updated.")
    
    # Remove any "admin:" prefix if it was there. 
    # It must match name='user-management' in your urls.py exactly.
    return redirect('user-management')