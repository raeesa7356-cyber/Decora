from itertools import product as cartesian_product

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Min
from .models import (
    Product, Category, Room,
    ProductVariant, VariantCombination, CombinationGallery)

from .forms import (
    CategoryForm, ProductForm, VariantValueForm, VariantForm,
    VariantCombinationForm, RoomForm)

from django.http import JsonResponse
from django.urls import reverse

def combination_meets_activation_criteria(combo):
    has_color = combo.variants.filter(variant_type='Color').exists()
    has_images = bool(combo.main_image) and combo.gallery.count() >= 3
    return has_color and has_images


def product_has_valid_combination(product):  
    combos = product.combinations.all()
    if not combos.exists():
        return False
    return all(combo.is_active for combo in combos)


def generate_sku(product, combo):
    parts = [v.variant_value[:3].upper() for v in combo.variants.all()]
    return f"{product.id}-{'-'.join(parts)}-{combo.id}"


def cleanup_incomplete_combinations(product):

    active_types = set(product.variants.filter(is_active=True).values_list('variant_type', flat=True).distinct())
    for combo in product.combinations.filter(is_active=False, original_price=0, stock_quantity=0, main_image=''):
        combo_types = set(combo.variants.values_list('variant_type', flat=True))
        if combo_types != active_types:
            combo.delete()


def generate_combinations_from_selection(product, selected_variant_ids):
   
    active_types = set(product.variants.filter(is_active=True).values_list('variant_type', flat=True).distinct())
    selected_variants = ProductVariant.objects.filter(id__in=selected_variant_ids, product=product, is_active=True)
    selected_by_type = {}
    
    for v in selected_variants:
        selected_by_type.setdefault(v.variant_type, []).append(v)

    missing_types = active_types - set(selected_by_type.keys())
    
    if missing_types:
        return None, f"Select at least one value for: {', '.join(sorted(missing_types))}."

    value_lists = list(selected_by_type.values())
    
    for combo in product.combinations.all():
        existing_types=set(combo.variants.values_list('variant_type',flat=True))
        if existing_types!=active_types:
            combo.delete()
            
    existing_sets = [frozenset(combo.variants.values_list('id', flat=True)) for combo in product.combinations.all()]

    created = []
    for combo_tuple in cartesian_product(*value_lists):
        variant_ids = frozenset(v.id for v in combo_tuple)
        if variant_ids in existing_sets:
            continue
        new_combo = VariantCombination.objects.create(product=product, original_price=0, stock_quantity=0, is_active=False)
        new_combo.variants.set(combo_tuple)
        new_combo.sku = generate_sku(product, new_combo)
        new_combo.save(update_fields=['sku'])
        existing_sets.append(variant_ids)
        created.append(new_combo)

    return created, None


            

def category_room_list(request):
    category_list = Category.objects.all().order_by('-is_active')

    search_query = request.GET.get('search', '')
    if search_query:
        category_list = category_list.filter(
            Q(name__icontains=search_query) |
            Q(product__room__name__icontains=search_query)
        ).distinct()

    cat_paginator = Paginator(category_list, 3)
    categories_page_obj = cat_paginator.get_page(request.GET.get('page'))

    room_queryset = Room.objects.all().order_by('name')
    if search_query:
        room_queryset = room_queryset.filter(Q(name__icontains=search_query))

    room_paginator = Paginator(room_queryset, 3)
    rooms_page_obj = room_paginator.get_page(request.GET.get('room_page'))

    context = {
        'categories': categories_page_obj,
        'rooms': rooms_page_obj,
        'active_menu': 'categories',
        'search_query': search_query
    }
    return render(request, 'admin_side/catalog/category_list.html', context)


def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            cat_obj = form.save(commit=False)
            cat_obj.is_active = form.cleaned_data['status'] == 'active'
            cat_obj.save()
            messages.success(request, "Updated successfully.")
            return redirect('catalog:category-list')
        else:
            messages.error(request, "Please fill in all required fields.")
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin_side/catalog/category_edit.html', {'form': form, 'category': category})


def restore_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = True
    category.save()
    messages.success(request, f"Category '{category.name}' is now active.")
    return redirect('catalog:category-list')


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            category.is_active = form.cleaned_data['status'] == 'active'
            category.save()
            messages.success(request, "Category added successfully!")
            return redirect('catalog:category-list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = CategoryForm()

    return render(request, 'admin_side/catalog/category_add.html', {'form': form})


def add_room(request):
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f"Room '{room.name}' created successfully.")
            return redirect('catalog:category-list')
    else:
        form = RoomForm()
    return render(request, 'admin_side/catalog/add_room.html', {'form': form})


def edit_room(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == "POST":
        room.name = request.POST.get('name')
        room.is_active = (request.POST.get('status') == 'active')
        room.save()
        messages.success(request, f"Room '{room.name}' updated successfully.")
        return redirect('catalog:category-list')
    return render(request, 'admin_side/catalog/edit_room.html', {'room': room})


  

def admin_product_list(request):
    categories = Category.objects.filter(is_active=True)
    rooms = Room.objects.filter(is_active=True)

    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    room_id = request.GET.get('room', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.select_related('category').prefetch_related(
        'variants', 'combinations', 'room'
    ).filter(
        is_active=True,
        combinations__is_active=True
    ).distinct().annotate(
        min_price=Min(
            'combinations__original_price',
            filter=Q(combinations__is_active=True)
        ))
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(combinations__sku__icontains=search_query)
        ).distinct()

    if category_id:
        products = products.filter(category_id=category_id)

    if room_id:
        products = products.filter(room=room_id)

    if min_price:
        products = products.filter(min_price__gte=min_price)

    if max_price:
        products = products.filter(min_price__lte=max_price)

    sort_option = request.GET.get('sort', 'newest')
    
    sort_map = {
        'newest': '-id',
        'oldest': 'id',
        'price_low': 'min_price',
        'price_high': '-min_price',
        'name_az': 'name',
        'name_za': '-name',
    }
    products = products.order_by(sort_map.get(sort_option, '-id'))

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    for product in page_obj:
        product.display_combination = product.default_combination
        product.variant_type_summary = (
            product.variants.values_list('variant_type', flat=True).distinct()
        )

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'sort_option': sort_option,
        'categories': categories,
        'rooms': rooms,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'selected_category': category_id,
        'selected_room': room_id,
        'search_query': search_query,
    }
    return render(request, 'admin_side/catalog/product_list.html', context)


def admin_product_archives(request):
    deleted_products = Product.objects.filter(is_active=False).order_by('-id')
    return render(request, 'admin_side/catalog/archieves.html', {
'products': deleted_products
})


def admin_product_restore(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if not product.combinations.exists():
        messages.error(request, "Cannot restore product. Add at least one combination.")
    elif not product_has_valid_combination(product):
        incomplete_count = product.combinations.filter(is_active=False).count()
        messages.error(
        request,
        f"Cannot restore product — {incomplete_count} combination(s) still incomplete. "
        "Every combination needs a Color value, a main image, and at least 3 gallery images "
        "before this product can go live."
    )
    else:
        product.is_active = True
        product.save()
        messages.success(request, f'"{product.name}" restored.')

    return redirect('catalog:admin_product_archives')


def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product.name}" has been moved to archives.')
        return redirect('catalog:admin-product-list')
    return redirect('catalog:admin-product-list')


def admin_product_upsert(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            with transaction.atomic():
                new_product = form.save(commit=False)
                if not pk:
                    new_product.is_active = False
                print("FORM ACTIVE:", form.cleaned_data['is_active'])
                print("COMBINATIONS VALID:", product_has_valid_combination(new_product))
                new_product.save()
                form.save_m2m()

                if pk:
                    if form.cleaned_data['is_active']:
                        if product_has_valid_combination(new_product):
                            new_product.is_active=True
                        else:
                            new_product.is_active=False
                            messages.error(request,'Activate all combinations before activating this product.')
                    else:
                        new_product.is_active=False        
                    new_product.save()

                    if new_product.combinations.exists() and not new_product.is_active:
                        messages.warning(
                            request,
                            "This product has been moved to the archive. To reactivate it, "
                            "please create or activate all variant combinations for this product first."

                        )
                        
                        return redirect('catalog:admin-product-edit', pk=product.id)
                    
                    else:
                        messages.success(request, "Product saved successfully.")
                else:
                    messages.success(request, "Product saved successfully.")

                return redirect('catalog:add_variant', product_id=new_product.id)            
        else:
            
            for field, errors in form.errors.items():
                if field == '__all__':
                    for error in errors:
                        messages.error(request, error)
                    continue
                field_name = (
                    form.fields[field].label
                    if field in form.fields
                    else field.replace('_', ' ').title()
                )
                
                for error in errors:
                    messages.error(request, f"{field_name}: {error}")
                    
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin_side/catalog/forms.html', {
        'form': form,
        'product': product,
        })



def admin_add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    existing_variants = product.variants.all().order_by('variant_type', 'variant_value')
    combinations = product.combinations.all().prefetch_related('variants', 'gallery').order_by('-id')

    if request.method == 'POST':
        form = VariantValueForm(request.POST)
        if form.is_valid():
            variant_type = form.cleaned_data['variant_type']
            values = form.cleaned_data['values']

            existing_values = {v.lower() for v in product.variants.filter(variant_type=variant_type).values_list('variant_value', flat=True)}

            created_count = 0
            for value in values:
                if value.lower() in existing_values:
                    continue
                ProductVariant.objects.create(
                    product=product,
                    variant_type=variant_type,
                    variant_value=value,
                )
                existing_values.add(value.lower())
                created_count += 1

            if created_count:
                messages.success(
                    request,
                    f"Added {created_count} {variant_type} value(s). "
                    "Select values below and click Generate to create combinations."
                )
                
            else:
                messages.info(request, "No new values added — they already exist.")

            return redirect('catalog:add_variant', product_id=product.id)
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)                   
    else:
        form = VariantValueForm()

    return render(request, 'admin_side/catalog/add_variant.html', {
        'form': form,
        'product': product,
        'existing_variants': existing_variants,
        'combinations': combinations,
    })


def admin_generate_combinations(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('generate_variants')
        if not selected_ids:
            messages.error(request, "Select at least one value from each attribute type first.")
            return redirect('catalog:add_variant', product_id=product.id)

        with transaction.atomic():
            cleanup_incomplete_combinations(product)
            created, error = generate_combinations_from_selection(product, selected_ids)

        if error:
            messages.error(request, error)
        elif not created:
            messages.info(request, "That combination already exists.")
        else:
            messages.success(request, f"{len(created)} combination(s) generated — add price and images to activate them.")

    return redirect('catalog:add_variant', product_id=product.id)

def admin_edit_variant(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    product = variant.product

    if request.method == 'POST':
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, "Value updated successfully.")
            return redirect('catalog:add_variant', product_id=product.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = VariantForm(instance=variant)

    return render(request, 'admin_side/catalog/add_variant.html', {
    'form': form,
    'variant': variant,
    'product': product,
})


def toggle_variant_status(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    product = variant.product

    if variant.variant_type == 'Color':
        other_colors = product.variants.filter(
            variant_type='Color', is_active=True
        ).exclude(pk=variant.pk)
        if not other_colors.exists():
            messages.error(request, "At least one Color value is required to generate combinations.")
            return redirect('catalog:add_variant', product_id=product.id)

    affected_count = variant.combinations.count()
    variant.combinations.all().delete()  
    variant.delete()

    product.is_active = product_has_valid_combination(product)
    product.save()

    if affected_count:
        messages.success(
            request,
            f"Value removed along with {affected_count} combination(s) that included it."
        )
    else:
        messages.success(request, "Variant value deleted successfully.")
    return redirect('catalog:add_variant', product_id=product.id)


def admin_manage_variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all()
    return render(request, 'admin_panel/products/variants.html', {
        'product': product,
        'variants': variants
    })



def admin_add_combination(request, product_id, pk=None):
    product = get_object_or_404(Product, id=product_id)
    combo = get_object_or_404(VariantCombination, pk=pk) if pk else None
    existing_gallery = combo.gallery.all().order_by('id') if combo else []
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = VariantCombinationForm(request.POST, request.FILES, instance=combo, product=product)
        form.fields['main_image'].required = False 

        if form.is_valid():

            existing_default_exists = product.combinations.exclude(
                pk=combo.pk if combo else None
            ).filter(is_default=True).exists()

            if not existing_default_exists and not form.cleaned_data.get('is_default'):
                msg = "No default combination is set yet — please check 'Set as default combination' before saving."
                if is_ajax:
                    return JsonResponse({'success': False, 'non_field_errors': [msg]}, status=400)
                
                messages.error(request, msg)
                return render(request, 'admin_side/catalog/add_combination.html', {
                    'form': form, 'product': product, 'combination': combo,
                    'existing_gallery': existing_gallery,
                    'selected_variant_ids': list(request.POST.getlist('variants')),
                })

            with transaction.atomic():
                new_combo = form.save(commit=False)
                new_combo.product = product

                if request.POST.get('delete_main_image') == 'true' and 'main_image' not in request.FILES:
                    new_combo.main_image = None

                new_combo.save()
                form.save_m2m()

                delete_ids = request.POST.getlist('delete_gallery_images')
                if delete_ids:
                    CombinationGallery.objects.filter(
                        id__in=delete_ids, combination=new_combo
                    ).delete()

                gallery_files = request.FILES.getlist('gallery_images')
                for f in gallery_files:
                    CombinationGallery.objects.create(combination=new_combo, image=f)

                if not new_combo.main_image:
                    msg = "A main image is required."
                    if is_ajax:
                        return JsonResponse({'success': False, 'non_field_errors': [msg]}, status=400)
                    messages.error(request, msg)
                    return render(request, 'admin_side/catalog/add_combination.html', {
                    'form': form, 'product': product, 'combination': new_combo,
                    'existing_gallery': new_combo.gallery.all().order_by('id'),
                    'selected_variant_ids': list(new_combo.variants.values_list('id', flat=True)),
                })

                if new_combo.gallery.count() < 3:
                    msg = "Each combination needs at least 3 gallery images."
                    if is_ajax:
                        return JsonResponse({'success': False, 'non_field_errors': [msg]}, status=400)
                    messages.error(request, msg)
                    return render(request, 'admin_side/catalog/add_combination.html', {
                    'form': form, 'product': product, 'combination': new_combo,
                    'existing_gallery': new_combo.gallery.all().order_by('id'),
                    'selected_variant_ids': list(new_combo.variants.values_list('id', flat=True)),
                })

                if not new_combo.sku:
                    new_combo.sku = generate_sku(product, new_combo)

                if form.cleaned_data.get('is_default'):
                    product.combinations.exclude(pk=new_combo.pk).update(is_default=False)
                    new_combo.is_default = True
                else:
                    new_combo.is_default = False

                new_combo.is_active = combination_meets_activation_criteria(new_combo)
                new_combo.save()

                product.is_active = product_has_valid_combination(product)
                product.save()

            success_msg = (
                "Combination saved and activated." if new_combo.is_active else
                "Combination saved but is inactive — it needs a Color value, a main image, "
                "and at least 3 gallery images to go live."
            )
            redirect_url = reverse('catalog:admin-product-edit', kwargs={'pk': product.id})

            if is_ajax:
                return JsonResponse({'success': True, 'redirect': redirect_url, 'message': success_msg})

            if new_combo.is_active:
                messages.success(request, success_msg)
            else:
                messages.info(request, success_msg)

            if not product.is_active and product.combinations.exists():
                messages.warning(
                    request,
                    "This product will stay in Archives until every combination is activated."
                )

            return redirect(redirect_url)

        else:
            if is_ajax:
                errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            for field, errors in form.errors.items():
                if field == '__all__':
                    for error in errors:
                        messages.error(request, error)
                    continue
                field_name = (
                    form.fields[field].label if field in form.fields else field.replace('_', ' ').title()
                )
                for error in errors:
                        messages.error(request, f"{field_name}: {error}")
    else:
        form = VariantCombinationForm(instance=combo, product=product)

    return render(request, 'admin_side/catalog/add_combination.html', {
        'form': form,
        'product': product,
        'combination': combo,
        'existing_gallery': existing_gallery,
        'selected_variant_ids': list(combo.variants.values_list('id', flat=True)) if combo else []
    })
def toggle_combination_status(request, pk):
    combo = get_object_or_404(VariantCombination, pk=pk)
    product = combo.product

    if product.combinations.count() <= 1:
        messages.error(request, "Cannot delete the only combination.")
        return redirect('catalog:add_variant', product_id=product.id)

    combo.delete()

    product.is_active = product_has_valid_combination(product)
    product.save()

    messages.success(request, "Combination deleted successfully.")
    return redirect('catalog:add_variant', product_id=product.id)