""" Serializers for models for a set of todo lists and items on those lists """
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import ToDoItem, ToDoList


# Multiple models have a primary key field called 'name'. Updating it will
# create a new model in the DB, so it needs to be prohibited. Django has
# no standard method to declare a field 'set-not-update' requiring the following
# mixin
# https://stackoverflow.com/questions/52686199/how-to-make-a-field-editable-false-in-drf
class ProhibitNameUpdateMixin:  # pylint: disable=too-few-public-methods
    """Prohibit changing the 'name' field in the serializer"""

    name = serializers.CharField(max_length=25)

    def validate_name(self, value):
        """Prohibit changing the 'name' field in the serializer"""
        if self.instance and self.instance.name != value:
            raise ValidationError("The name field may not be updated")
        return value


class ToDoListSerializer(serializers.ModelSerializer, ProhibitNameUpdateMixin):
    """Serializer for a todo list"""

    class Meta:
        model = ToDoList
        fields = ("name", "description", "created_at", "updated_at")


class ToDoItemSerializer(serializers.ModelSerializer, ProhibitNameUpdateMixin):
    """Serializer for a itme on a todo list"""

    class Meta:
        model = ToDoItem
        fields = (
            "name",
            "description",
            "to_do_list",
            "priority",
            "created_at",
            "updated_at",
        )

    # The model has a unique_together constraint that is handled by modifying records in the
    # view. It should not be enforced in the serializer. Since it is the only one in the model,
    # this is the easiest way of doing so
    # https://stackoverflow.com/questions/45999131/django-rest-framework-model-serializer-with-out-unique-together-validation
    def get_unique_together_validators(self):
        """Overriding method to disable unique together checks"""
        return []
