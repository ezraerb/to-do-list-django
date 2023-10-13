""" URL paths to support the todo list app """
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from todolist import views

app_name = "todolist"

urlpatterns = [
    path("api/v1/todolist/", views.ToDoListMult.as_view(), name="todolistmult"),
    path(
        "api/v1/todolist/<slug:name>/",
        views.ToDoListSingle.as_view(),
        name="todolistsingle",
    ),
    path(
        "api/v1/todolist/<slug:name>/with_items",
        views.ToDoListWithItems.as_view(),
        name="todolistwithitems",
    ),
    path("api/v1/todoitem/", views.ToDoItemMult.as_view(), name="todoitemmult"),
    path(
        "api/v1/todoitem/<slug:name>/",
        views.ToDoItemSingle.as_view(),
        name="todoitemsingle",
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)
