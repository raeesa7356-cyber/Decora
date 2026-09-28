from django.urls import path
from . import views

app_name = "admin_inspiration"

urlpatterns = [
    path("", views.inspiration_list, name="list"),
    path("create/", views.inspiration_create, name="create"),
    path("<int:id>/edit/", views.inspiration_edit, name="edit"),
    path("<int:id>/delete/", views.inspiration_delete, name="delete"),
    path(
    "styles/",
    views.style_list,
    name="style_list"
),

path(
    "styles/create/",
    views.style_create,
    name="style_create"
),

path(
    "tags/",
    views.tag_list,
    name="tag_list"
),

path(
    "tags/create/",
    views.tag_create,
    name="tag_create"
),
path(
    "tags/<int:id>/edit/",
    views.tag_edit,
    name="tag_edit"
),

path(
    "tags/<int:id>/delete/",
    views.tag_delete,
    name="tag_delete"
),
path(
    "styles/<int:id>/edit/",
    views.style_edit,
    name="style_edit"
),

path(
    "styles/<int:id>/delete/",
    views.style_delete,
    name="style_delete"
),
]
