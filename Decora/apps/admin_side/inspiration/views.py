from django.shortcuts import (render,redirect,get_object_or_404)
from django.contrib.admin.views.decorators import (staff_member_required)
from django.contrib import messages
from apps.user_side.inspiration.models import (
    InspirationBoard,
    InspirationImage,
    InspirationStyle,
    InspirationTag,
)
from .forms import (InspirationForm,InspirationGalleryForm)
from .forms import (
    InspirationForm,
    StyleForm,
    TagForm,
)
# =========================
# LIST
# =========================
@staff_member_required
def inspiration_list(request):

    boards = (
        InspirationBoard.objects
        .prefetch_related(
            "rooms",
            "categories",
            "products"
        )
        .order_by(
            "priority",
            "-created_at"
        )
    )

    return render(
request,
"admin_side/inspiration/admin_list.html",
{
    "boards": boards
}
)


# =========================
# CREATE
# =========================
@staff_member_required
def inspiration_create(request):

    if request.method == "POST":

        form = InspirationForm(
            request.POST,
            request.FILES
        )

        gallery_files = request.FILES.getlist(
            "gallery_images"
        )

        if form.is_valid():

            board = form.save()

            # SAVE GALLERY IMAGES
            for image in gallery_files:

                InspirationImage.objects.create(
                    board=board,
                    image=image
                )

            messages.success(
                    request,
                    "Inspiration created successfully"
                )

            if request.POST.get("stay_on_page") == "1":

                return redirect(
                "admin_inspiration:edit",
                id=board.id
            )

            return redirect(
                "admin_inspiration:list"
            )

    else:
        form = InspirationForm()

    return render(
                request,
                "admin_side/inspiration/add_inspiration.html",
                {
                    "form": form
                }
            )


            # =========================
            # EDIT
            # =========================
@staff_member_required
def inspiration_edit(request, id):

    board = get_object_or_404(
        InspirationBoard,
        id=id
    )

    if request.method == "POST":

        form = InspirationForm(
            request.POST,
            request.FILES,
            instance=board
        )

        gallery_files = request.FILES.getlist(
            "gallery_images"
        )

        if form.is_valid():

            board = form.save()

            # ADD NEW GALLERY IMAGES
            for image in gallery_files:

                InspirationImage.objects.create(
                    board=board,
                    image=image
                )

            messages.success(
                    request,
                    "Inspiration updated successfully"
                )

            if request.POST.get("stay_on_page") == "1":

                return redirect(
                "admin_inspiration:edit",
                id=board.id
            )

            return redirect(
                "admin_inspiration:list"
            )

    else:

        form = InspirationForm(
                        instance=board
                    )

    return render(
                request,
                "admin_side/inspiration/add_inspiration.html",
                {
                    "form": form,
                    "board": board,
                    "edit_mode": True,
                    "gallery": board.gallery.all()
                }
            )


            # =========================
            # DELETE BOARD
            # =========================
@staff_member_required
def inspiration_delete(request, id):

    board = get_object_or_404(
        InspirationBoard,
        id=id
    )

    board.delete()

    messages.success(
        request,
        "Inspiration deleted successfully"
    )

    return redirect(
"admin_inspiration:list"
)


# =========================
# DELETE GALLERY IMAGE
# =========================
@staff_member_required
def inspiration_gallery_delete(
    request,
    id
):

    image = get_object_or_404(
        InspirationImage,
        id=id
    )

    board_id = image.board.id

    image.delete()

    messages.success(
        request,
        "Gallery image removed"
    )

    return redirect(
"admin_inspiration:edit",
id=board_id
)
@staff_member_required
def style_list(request):

    styles = InspirationStyle.objects.all().order_by("name")

    return render(
request,
"admin_side/inspiration/style_list.html",
{
    "styles": styles
}
)
@staff_member_required
def style_create(request):

    if request.method == "POST":

        form = StyleForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Style created successfully"
            )

            return redirect(
        "admin_inspiration:style_list"
    )

    else:
        form = StyleForm()

    return render(
        request,
        "admin_side/inspiration/style_create.html",
        {
            "form": form
        }
    )     
@staff_member_required
def tag_list(request):

    tags = InspirationTag.objects.all().order_by("name")

    return render(
request,
"admin_side/inspiration/tag_list.html",
{
    "tags": tags
}
)   
@staff_member_required
def tag_create(request):

    if request.method == "POST":

        form = TagForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Tag created successfully"
            )

            return redirect(
        "admin_inspiration:tag_list"
    )

    else:
        form = TagForm()

    return render(
        request,
        "admin_side/inspiration/tag_create.html",
        {
            "form": form
        }
    )
@staff_member_required
def tag_edit(request, id):

    tag = get_object_or_404(
        InspirationTag,
        id=id
    )

    if request.method == "POST":

        tag.name = request.POST.get("name")
        tag.save()

        messages.success(
            request,
            "Tag updated successfully"
        )

        return redirect(
    "admin_inspiration:tag_list"
)

    return render(
request,
"admin_side/inspiration/tag_create.html",
{
    "tag": tag
}
)


@staff_member_required
def tag_delete(request, id):

    tag = get_object_or_404(
        InspirationTag,
        id=id
    )

    tag.delete()

    messages.success(
        request,
        "Tag deleted successfully"
    )

    return redirect(
"admin_inspiration:tag_list"
)     
@staff_member_required
def style_edit(request, id):

    style = get_object_or_404(
        InspirationStyle,
        id=id
    )

    if request.method == "POST":

        form = StyleForm(
            request.POST,
            instance=style
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Style updated successfully"
            )

            return redirect(
        "admin_inspiration:style_list"
    )

    else:

        form = StyleForm(
                instance=style
            )

    return render(
        request,
        "admin_side/inspiration/style_create.html",
        {
            "form": form,
            "edit_mode": True
        }
    )

@staff_member_required
def style_delete(request, id):

    style = get_object_or_404(
        InspirationStyle,
        id=id
    )

    style.delete()

    messages.success(
        request,
        "Style deleted successfully"
    )

    return redirect(
"admin_inspiration:style_list"
)    