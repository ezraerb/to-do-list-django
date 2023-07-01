""" Test for todolist application models """
from django.db.utils import IntegrityError
from django.test import TestCase
from ..models import ToDoList, ToDoItem


class ToDoListTest(TestCase):
    """Tests for the To Do List model"""

    def setUp(self):
        ToDoList.objects.create(name="FirstList", description="First Test List")
        ToDoList.objects.create(name="SecondList", description="Second Test List")

    def test_repr(self):
        """Test the model representation"""
        first_to_do_list = ToDoList.objects.get(name="FirstList")
        self.assertEqual(repr(first_to_do_list), "FirstList: First Test List")

    def test_duplicate_name_raises(self):
        """Validate that the name must be unique"""
        with self.assertRaises(IntegrityError):
            ToDoList.objects.create(
                name="SecondList", description="Second attempt second Test List"
            )


class ToDoListItem(TestCase):
    """Tests for the To Do List item model"""

    def setUp(self):
        self.first_list = ToDoList.objects.create(
            name="FirstList", description="First Test List"
        )
        self.second_list = ToDoList.objects.create(
            name="SecondList", description="Second Test List"
        )
        ToDoItem.objects.create(
            name="FirstItem",
            description="First Test Item",
            to_do_list=self.first_list,
            priority=1,
        )

    def test_repr(self):
        """Test the model representation"""
        first_to_do_item = ToDoItem.objects.get(name="FirstItem")
        self.assertEqual(repr(first_to_do_item), "FirstItem: First Test Item")

    def test_duplicate_name_raises(self):
        """Validate that the name must be unique, even when it is in another list"""
        with self.assertRaises(IntegrityError):
            ToDoItem.objects.create(
                name="FirstItem",
                description="Second attempt first Test Item",
                to_do_list=self.second_list,
                priority=1,
            )

    def test_invalid_priority_raises(self):
        """Validate that the priority must be valid"""
        with self.assertRaises(ValueError):
            ToDoItem.objects.create(
                name="InvalidItem",
                description="Invalid priority",
                to_do_list=self.second_list,
                priority="Not a number",
            )

    def test_same_priority_diff_lists_creates_item(self):
        """Validate that a duplicate priority is allowed when the lists are different"""
        try:
            ToDoItem.objects.create(
                name="NewItem",
                description="New Test Item",
                to_do_list=self.second_list,
                priority=1,
            )
        except IntegrityError:
            self.fail(
                "Inserting in second to do list with same priority raised IntegrityError"
            )

    def test_same_priority_same_list_raises(self):
        """
        Validate that attempting to insert a second item with the same priority
        in a list raises
        """
        with self.assertRaises(IntegrityError):
            ToDoItem.objects.create(
                name="NewItem",
                description="New Test Item",
                to_do_list=self.first_list,
                priority=1,
            )
