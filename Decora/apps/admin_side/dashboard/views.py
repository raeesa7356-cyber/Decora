from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.admin_side.orders.models import Order, OrderItem
from apps.admin_side.catalog.models import Product, Category


def admin_login_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin-dashboard')
        else:
            messages.error(request, "Invalid Admin Credentials")
            return redirect('admin-login')
    return render(request, 'admin_side/dashboard/login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('admin-login')


@staff_member_required
def admin_dashboard_view(request):
    now = timezone.now()
    period = request.GET.get('period', 'monthly')

    # ✅ include PENDING so test orders appear
    valid_statuses = ['PENDING', 'ACTIVE', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']

    # ─── STATS CARDS ───────────────────────────────────────────────
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        status__in=valid_statuses
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_users = User.objects.filter(is_staff=False).count()
    total_products = Product.objects.filter(is_active=True).count()

    stats = [
        {'title': 'Total Orders', 'value': total_orders, 'growth': '', 'icon': 'bag-shopping'},
        {'title': 'Total Revenue', 'value': f'₹{total_revenue:,.2f}', 'growth': '', 'icon': 'wallet'},
        {'title': 'Total Users', 'value': total_users, 'growth': '', 'icon': 'user-plus'},
        {'title': 'Total Products', 'value': total_products, 'growth': 'Active', 'icon': 'clipboard-check'},
    ]

    # ─── CHART DATA ────────────────────────────────────────────────
    if period == 'daily':
        labels, data = [], []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            revenue = Order.objects.filter(
                status__in=valid_statuses,
                created_at__date=day.date()
            ).aggregate(t=Sum('total_amount'))['t'] or 0
            labels.append(day.strftime('%d %b'))
            data.append(float(revenue))

    elif period == 'weekly':
        labels, data = [], []
        for i in range(7, -1, -1):
            week_start = now - timedelta(weeks=i+1)
            week_end = now - timedelta(weeks=i)
            revenue = Order.objects.filter(
                status__in=valid_statuses,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(t=Sum('total_amount'))['t'] or 0
            labels.append(f"W{week_start.strftime('%W')}")
            data.append(float(revenue))

    elif period == 'yearly':
        labels, data = [], []
        for i in range(4, -1, -1):
            year = now.year - i
            revenue = Order.objects.filter(
                status__in=valid_statuses,
                created_at__year=year
            ).aggregate(t=Sum('total_amount'))['t'] or 0
            labels.append(str(year))
            data.append(float(revenue))

    else:  # monthly
        labels, data = [], []
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30 * i)
            revenue = Order.objects.filter(
                status__in=valid_statuses,
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).aggregate(t=Sum('total_amount'))['t'] or 0
            labels.append(month_date.strftime('%b %Y'))
            data.append(float(revenue))

            # ─── TOP PRODUCTS ──────────────────────────────────────────────
    top_products = (
        OrderItem.objects
        .filter(order__status__in=valid_statuses)
        .values('product__id', 'product__name')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum('total_price'))
        .order_by('-total_qty')[:5]
    )

            # ─── TOP CATEGORIES ────────────────────────────────────────────
    top_categories = (
        OrderItem.objects
        .filter(order__status__in=valid_statuses)
        .values('product__category__name')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum('total_price'))
        .order_by('-total_qty')[:5]
    )

            # ─── RECENT ORDERS ─────────────────────────────────────────────
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:8]

    context = {
        'stats': stats,
        'chart_labels': labels,
        'chart_data': data,
        'period': period,
        'top_products': top_products,
        'top_categories': top_categories,
        'recent_orders': recent_orders,
                # ✅ THIS WAS MISSING — caused template error
        'period_options': [
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
    }
    return render(request, 'admin_side/dashboard/dashboard.html', context)