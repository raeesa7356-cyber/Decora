# admin/context_processors.py

def sidebar_context(request):
    return {
        'sidebar_items': [
            ('Dashboard', 'table-columns', 'admin-dashboard'), # Keep this if it works
            ('Products', 'box', '#'),                          # Change to '#'
            ('Orders', 'cart-shopping', '#'),                  # Change to '#'
            # context_processors.py
            ('Users', 'users', 'user-management'), # Matches name='user-list' in urls.py                          # Change to '#'
            ('Categories', 'layer-group', '#'),                # Change to '#'
            ('Inventory', 'warehouse', '#'),                   # Change to '#'
            ('Coupons', 'ticket', '#'),                        # Change to '#'
            ('Reviews', 'star', '#'),                          # Change to '#'
            ('Banners', 'image', '#'),                         # Change to '#'
            ('Reports', 'chart-line', '#'),                    # Change to '#'
            ('Returns', 'rotate-left', '#'),                   # Change to '#'
            ('Offers', 'tags', '#'),                           # Change to '#'
        ]
    }