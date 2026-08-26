from django.shortcuts import render, get_object_or_404,redirect
from .models import InspirationBoard, InspirationStyle, InspirationTag
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .models import InspirationImage
from apps.admin_side.catalog.models import Room

app_name = "user_inspiration"


def inspiration_list(request):

    boards = (
        InspirationBoard.objects
        .filter(is_active=True)
        .select_related("style")
        .prefetch_related("rooms", "categories", "tags", "gallery")
        .order_by("priority", "-created_at")
    )

    style_id = request.GET.get("style")
    room_id = request.GET.get("room")
    tag_id = request.GET.get("tag")

    if style_id:
        boards = boards.filter(style__id=style_id)

    if room_id:
        boards = boards.filter(rooms__id=room_id)

    if tag_id:
        boards = boards.filter(tags__id=tag_id)

    boards = boards.distinct()

               
    featured_board = None
    if not (style_id or room_id or tag_id):
        featured_board = boards.filter(is_featured=True).first()

    other_boards = boards.exclude(pk=featured_board.pk) if featured_board else boards

    context = {
        "featured_board": featured_board,
        "boards": other_boards,
        "styles": InspirationStyle.objects.filter(is_active=True).order_by("name"),
        "rooms": Room.objects.filter(is_active=True).order_by("name"),
        "tags": InspirationTag.objects.all().order_by("name"),
        "active_style": int(style_id) if style_id else None,
        "active_room": int(room_id) if room_id else None,
        "active_tag": int(tag_id) if tag_id else None,
    }

    return render(request, "user_side/inspiration/list.html", context)


def inspiration_detail(request, pk):

    board = get_object_or_404(
        InspirationBoard.objects
        .select_related("style")
        .prefetch_related("gallery", "tags", "rooms", "categories", "products"),
        pk=pk,
        is_active=True,
    )

    
    for product in board.products.all():
        active_variants = list(product.variants.filter(is_active=True))

        if not active_variants:
            product.shop_variant = None
            continue

        image_variant = next(
            (v for v in active_variants if v.variant_image or v.gallery.exists()),
            active_variants[0]
        )
        product.shop_variant = image_variant

    related_boards = (
        InspirationBoard.objects
        .filter(is_active=True, style=board.style)
        .exclude(pk=board.pk)[:3]
    ) if board.style_id else InspirationBoard.objects.none()

    return render(request, "user_side/inspiration/detail.html", {
    "board": board,
    "related_boards": related_boards,
})



@staff_member_required
def gallery_set_product(request, id):

    image = get_object_or_404(InspirationImage, id=id)

    if request.method == "POST":
        product_id = request.POST.get("product")
        image.product_id = product_id or None
        image.save()
        messages.success(request, "Product linked to image")

        return redirect("admin_inspiration:edit", id=image.board.id)    
