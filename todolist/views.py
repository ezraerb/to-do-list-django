""" URL views for todo list and item related tasks """
from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response

from .models import ToDoItem, ToDoList
from .serializers import ToDoItemSerializer, ToDoListSerializer


class ToDoListMult(generics.ListCreateAPIView):
    """Views for URLs that do not specify a todo list. Use standard behavior for all"""

    queryset = ToDoList.objects.all()
    serializer_class = ToDoListSerializer


class ToDoListSingle(generics.RetrieveUpdateDestroyAPIView):
    """Views for URLs that specify a particular todo list. Use standard behavior for all"""

    queryset = ToDoList.objects.all()
    serializer_class = ToDoListSerializer
    lookup_field = "name"


class ToDoListWithItems(generics.RetrieveAPIView):
    """View for URL to fetch a todo list and the items in the list"""

    queryset = ToDoList.objects.all()
    serializer_class = ToDoListSerializer
    lookup_field = "name"

    def get(self, request, *args, **kwargs):
        """Retrieve the todolist with all of its items in priority order"""
        to_do_list = self.get_object()
        to_do_list_serializer = ToDoListSerializer(to_do_list)

        to_do_items = ToDoItem.objects.filter(to_do_list=to_do_list)
        to_do_items_serializer = ToDoItemSerializer(to_do_items, many=True)
        return Response(
            {"list": to_do_list_serializer.data, "items": to_do_items_serializer.data}
        )


class MoveExistingItemsMixin:  # pylint: disable=too-few-public-methods
    """
    If the wanted priority of a given todo list item clashes with ane existing
    item, the existing items are decreased in priority to make room
    WARNING: All methods in this class must be called from methods that are atomic
    """

    def move_items_priority_if_needed(self, item_data) -> None:
        """
        Find items that need to have their priority lowered to make room for an item
        with the given priority, and update them. The item data must already be validated
        NOTE: In todo lists, lower priority items have a higher number
        """
        # Items are moved by increasing each priority value by 1 (which lowers the priority).
        # If that results in a clash, the next item is also moved, etc. Items are fetched in
        # priority order by default, so this is a linear process
        priority_to_move = item_data["priority"]
        items_to_save = []
        items_to_move = self.get_queryset().filter(
            to_do_list=item_data["to_do_list"], priority__gte=priority_to_move
        )
        for item in items_to_move:
            if item.priority > priority_to_move:
                break
            # If the item being updated is itself fetched, it means it is being updated to have a
            # higher priority within the same todo list. Set it to zero for this update to make room
            # for the item that will take its place found in the previous pass. The loop can stop
            # afterwards since no further items will need to be moved
            if item.name == item_data["name"]:
                item.priority = (
                    0  # Will be replaced later when entire record is updated
                )
                items_to_save.append(item)
                break
            priority_to_move += 1
            item.priority = priority_to_move
            items_to_save.append(item)
        # Since items are increasing in priority, need to save them in reverse order of
        # priority. Unfortunately, the uniqueness constraint on priority prevents doing a
        # bulk update
        items_to_save.reverse()
        for item in items_to_save:
            item.save()


class ToDoItemMult(generics.ListCreateAPIView, MoveExistingItemsMixin):
    """
    Views for URLs that do not specify a todo item. Use standard behavior
    for all except create
    """

    queryset = ToDoItem.objects.all()
    serializer_class = ToDoItemSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create a new todo item, decreasing the priority of other items as needed. Overrides a
        method in the base class
        """

        self.move_items_priority_if_needed(serializer.validated_data)
        return super().perform_create(serializer)


# pylint: disable=too-many-ancestors
class ToDoItemSingle(generics.RetrieveUpdateDestroyAPIView, MoveExistingItemsMixin):
    """Views for URLs that specify a todo item. Use standard behavior for all except update"""

    queryset = ToDoItem.objects.all()
    serializer_class = ToDoItemSerializer
    lookup_field = "name"

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Perform the requested update of the todo item, moving other item priorities
        to make room if necessary. Overrides a method in the base class
        """

        # If the update data has both a todo list and a priority, it can be used to directly
        # do the priority adjustment of other items
        if (
            "to_do_list" in serializer.validated_data
            and "priority" in serializer.validated_data
        ):
            self.move_items_priority_if_needed(serializer.validated_data)
        elif (
            "to_do_list" in serializer.validated_data
            or "priority" in serializer.validated_data
        ):
            # Priority or todo list was changed. Need to adjust priorities based on information
            # in the instance
            instance_data = {
                "name": serializer.instance.name,
                "to_do_list": serializer.validated_data.get(
                    "to_do_list", serializer.instance.to_do_list
                ),
                "priority": serializer.validated_data.get(
                    "priority", serializer.instance.priority
                ),
            }
            self.move_items_priority_if_needed(instance_data)
        return super().perform_update(serializer)
