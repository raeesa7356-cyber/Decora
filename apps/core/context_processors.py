from apps.user_side.accounts.models import Profile
from apps.user_side.cart.models import Cart
from apps.user_side.shop.models import Wishlist

def global_context(request):
    context={
        'cart_count':0,
        'wishlist_count':0,
        'user_profile':None,
        'sidebar_items': [
            ('Dashboard','table-columns','admin-dashboard'),
            ('Products','box','catalog:admin-product-list'),
            ('Orders','cart-shopping','admin_order_list'),
            ('Transaction','receipt','wallet_transaction_list'),
            ('Users','users','user-management'),
            ('Categories','layer-group','catalog:category-list'),
            ('Archives','box-archive','catalog:admin_product_archives'),
            ('Inventory','warehouse','inventory_list'),
            ('Coupons','ticket','coupon_list'),
            ('Reviews','star','admin_reviews'),
            ('Inspiration','image','admin_inspiration:list'),
            ('Reports','chart-line','sales_report'),
            ('Returns','rotate-left','admin_return_requests'),
            ('Offers','tags','offer_list'),
        ]
    }
    
    if request.user.is_authenticated:
        context['cart_count']=Cart.objects.filter(user=request.user).count()
        context['wishlist_count']=Wishlist.objects.filter(user=request.user).count()
        try:
            user_profile=Profile.objects.filter(user=request.user)
        except Profile.DoesNotExist:
            pass
    return context    
                
        
    