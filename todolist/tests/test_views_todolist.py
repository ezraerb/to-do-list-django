""" Tests for todo list view methods """
from copy import copy
import json
from rest_framework import status
from django.test import TestCase, Client
from django.urls import reverse
from ..models import ToDoList, ToDoItem
from ..serializers import ToDoListSerializer, ToDoItemSerializer
from .test_utils import strip_timestamps

# initialize the APIClient app
client = Client()


def init_db() -> dict:
    """Initialize DB for tests and return data as a map"""
    test_data = {
        "FirstList": "First to do list",
        "SecondList": "Second to do list",
        "ThirdList": "Third to do list",
    }
    result = {}
    for name, description in test_data.items():
        result[name] = ToDoList.objects.create(name=name, description=description)
    return result


class GetAllToDoListTest(TestCase):
    """Test module for GET all to do lists API"""

    def setUp(self):
        self.records = init_db()

    def test_get_all_todo_lists_returns_records(self):
        """Get all records"""
        response = client.get(reverse("todolist:todolistmult"))
        serializer = ToDoListSerializer(self.records.values(), many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetSingleToDoListTest(TestCase):
    """Test module for GET single todolist API"""

    def setUp(self):
        self.records = init_db()

    def test_get_valid_single_todolist_returns_it(self):
        """Get single record that exists"""
        test_name = "SecondList"
        response = client.get(
            reverse("todolist:todolistsingle", kwargs={"name": test_name})
        )
        serializer = ToDoListSerializer(self.records[test_name])
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_invalid_single_todolist_returns_404(self):
        """Get single record that does not exist"""
        response = client.get(
            reverse("todolist:todolistsingle", kwargs={"name": "invalid"})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PostSingleToDoListTest(TestCase):
    """Test module for POST single todolist API"""

    def setUp(self):
        self.records = init_db()

    def test_post_valid_todolist_inserts_it(self):
        """Posting a valid record with an unused name inserts it"""

        test_name = "FourthList"
        valid_payload = {"name": test_name, "description": "Fourth to do list"}
        response = client.post(
            reverse("todolist:todolistmult"),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch the record from the DB and validate it was inserted
        test_record = ToDoList.objects.get(name=test_name)
        serializer = ToDoListSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_post_invalid_todolist_returns_400(self):
        """Posting an invalid record returns a 400"""

        invalid_payload = {"name": "", "description": "Invalid to do list"}
        response = client.post(
            reverse("todolist:todolistmult"),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_duplicate_todolist_name_returns_400(self):
        """Posting a record with a name already in use returns a 400"""

        test_name = self.records["SecondList"].name
        invalid_payload = {"name": test_name, "description": "Invalid to do list"}
        response = client.post(
            reverse("todolist:todolistmult"),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Validate that the duplicate record was not inserted. Can't use get()
        # here since it will raise if the insert succeeded
        records = ToDoList.objects.filter(name=test_name)
        self.assertEqual(len(records), 1)


class PutSingleToDoListTest(TestCase):
    """Test module for PUT single todolist API"""

    def setUp(self):
        self.records = init_db()

    def test_put_valid_todolist_updates_it(self):
        """Updating a valid record with valid data updatess it"""

        test_name = self.records["SecondList"].name
        valid_payload = {
            "name": test_name,
            "description": "Still the second to do list",
        }
        response = client.put(
            reverse("todolist:todolistsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch the record from the DB and validate it was updated
        test_record = ToDoList.objects.get(name=test_name)
        serializer = ToDoListSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_put_change_todolist_name_returns_400(self):
        """Attempting to update the todlist name returns an error"""

        old_name = self.records["SecondList"].name
        new_name = "InvalidList"
        invalid_payload = {"name": new_name, "description": "Invalid to do list"}
        response = client.put(
            reverse("todolist:todolistsingle", kwargs={"name": old_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Since 'name' is the primary key, a successful DB update would have duplicated
        # the existing record with the new primary key value. Validate that one does
        # NOT exist. Can't use get() here since it will raise if the record does not exist
        records = ToDoList.objects.filter(name=new_name)
        self.assertEqual(len(records), 0)


class PatchSingleToDoListTest(TestCase):
    """Test module for PATCH single todolist API"""

    def setUp(self):
        self.records = init_db()

    def test_patch_valid_todolist_updates_it(self):
        """Updating a valid record with valid data updatess it"""

        test_name = self.records["SecondList"].name
        valid_payload = {"description": "Still the second to do list"}
        response = client.patch(
            reverse("todolist:todolistsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)

        # Need to inject the non-changed fields into the expected results
        expected_results = copy(valid_payload)
        expected_results["name"] = test_name
        self.assertEqual(returned_data, expected_results)

        # Fetch the record from the DB and validate it was updated
        test_record = ToDoList.objects.get(name=test_name)
        serializer = ToDoListSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_patch_change_todolist_name_returns_400(self):
        """Attempting to update the todlist name returns an error"""

        old_name = self.records["SecondList"].name
        new_name = "InvalidList"
        invalid_payload = {"name": new_name}
        response = client.patch(
            reverse("todolist:todolistsingle", kwargs={"name": old_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Since 'name' is the primary key, a successful DB update would have duplicated
        # the existing record with the new primary key value. Validate that one does
        # NOT exist. Can't use get() here since it will raise if the record does not exist
        records = ToDoList.objects.filter(name=new_name)
        self.assertEqual(len(records), 0)


class DeleteSingleToDoListTest(TestCase):
    """Test module for DELETE single todolist API"""

    def setUp(self):
        self.records = init_db()

    def test_delete_valid_todolist_removes_it(self):
        """Deleting a valid record removes it"""

        test_name = self.records["SecondList"].name
        response = client.delete(
            reverse("todolist:todolistsingle", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

        # Fetch the record from the DB and validate it no longer exists. Can't
        # use get() here since it will raise if the record does not exist
        records = ToDoList.objects.filter(name=test_name)
        self.assertEqual(len(records), 0)

    def test_delete_todolist_removes_items(self):
        """Deleteing a todolist also removes all todoitems in the list"""
        test_list = self.records["SecondList"]
        ToDoItem.objects.create(
            name="FirstItem",
            description="First Test Item",
            to_do_list=test_list,
            priority=1,
        )
        ToDoItem.objects.create(
            name="SecondItem",
            description="Second Test Item",
            to_do_list=test_list,
            priority=2,
        )

        response = client.delete(
            reverse("todolist:todolistsingle", kwargs={"name": test_list.name})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

        # Fetch the items in the list and validate that they are gone
        records = ToDoItem.objects.filter(to_do_list=test_list)
        self.assertEqual(len(records), 0)

    def test_delete_non_existent_name_returns_404(self):
        """Attempting to delete a non-existent todlist returns an error"""

        test_name = "InvalidList"
        response = client.delete(
            reverse("todolist:todolistsingle", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GettoDoListWithItemsTest(TestCase):
    """Test fetching ToDoLists with items included"""

    def setUp(self):
        self.todolists = init_db()
        # Create second item first, to show sorting works properly
        self.second_item = ToDoItem.objects.create(
            name="SecondItem",
            description="Second Test Item",
            to_do_list=self.todolists["SecondList"],
            priority=2,
        )
        self.first_item = ToDoItem.objects.create(
            name="FirstItem",
            description="First Test Item",
            to_do_list=self.todolists["SecondList"],
            priority=1,
        )

    def test_get_valid_todo_list_no_items_returns_it(self):
        """Fetching a todo list with no items works"""

        test_name = "FirstList"
        response = client.get(
            reverse("todolist:todolistwithitems", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = ToDoListSerializer(self.todolists[test_name])
        self.assertEqual(response.data, {"list": serializer.data, "items": []})

    def test_get_valid_todo_list_with_items_returns_it(self):
        """Fetching a todo list with no items works"""

        test_name = "SecondList"
        response = client.get(
            reverse("todolist:todolistwithitems", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        list_serializer = ToDoListSerializer(self.todolists[test_name])
        first_item_serializer = ToDoItemSerializer(self.first_item)
        second_item_serializer = ToDoItemSerializer(self.second_item)
        self.assertEqual(
            response.data,
            {
                "list": list_serializer.data,
                "items": [first_item_serializer.data, second_item_serializer.data],
            },
        )

    def test_get_invalid_todolist_with_items_returns_404(self):
        """Feching a todo list with items where the list does not exist"""
        response = client.get(
            reverse("todolist:todolistwithitems", kwargs={"name": "invalid"})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
