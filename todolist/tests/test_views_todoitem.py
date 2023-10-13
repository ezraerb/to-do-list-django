""" Tests for views related to todo item manipulation """
import json
from copy import copy

from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status

from ..models import ToDoItem, ToDoList
from ..serializers import ToDoItemSerializer
from .test_utils import strip_timestamps

# initialize the APIClient app
client = Client()


class ToDoItemViewTestBase(TestCase):
    """Base class for ToDoItem view tests with common functionality"""

    def init_db(self):
        """Initialize DB for tests and return data as a map"""
        # pylint: disable=attribute-defined-outside-init
        self.to_do_list = ToDoList.objects.create(
            name="TestList", description="Test to do list"
        )
        self.other_to_do_list = ToDoList.objects.create(
            name="OtherTestList", description="Other Test to do list"
        )

        test_data = {
            "FirstItem": {
                "description": "First to do item",
                "priority": 1,
            },
            "SecondItem": {
                "description": "Second to do item",
                "priority": 2,
            },
            "ThirdItem": {
                "description": "Third to do item",
                "priority": 3,
            },
        }
        self.records = {}
        for name, values in test_data.items():
            self.records[name] = ToDoItem.objects.create(
                name=name,
                description=values["description"],
                to_do_list=self.to_do_list,
                priority=values["priority"],
            )

        # Add one item in the other todo list
        self.other_list_item = ToDoItem.objects.create(
            name="OtherFirstTodoItem",
            description="Other list first todo item",
            to_do_list=self.other_to_do_list,
            priority=1,
        )


class GetAllToDoItemTest(ToDoItemViewTestBase):
    """Test module for GET all to do items API"""

    def setUp(self):
        self.init_db()

    def test_get_all_todo_items_returns_records(self):
        """Get all records"""
        response = client.get(reverse("todolist:todoitemmult"))
        # Lists are sorted in alphabetical order, so the other list sorts first
        records = [self.other_list_item] + list(self.records.values())
        serializer = ToDoItemSerializer(records, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetSingleToDoItemTest(ToDoItemViewTestBase):
    """Test module for GET single todoitem API"""

    def setUp(self):
        self.init_db()

    def test_get_valid_single_todoitem_returns_it(self):
        """Get single record that exists"""
        test_name = "SecondItem"
        response = client.get(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name})
        )
        serializer = ToDoItemSerializer(self.records[test_name])
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_invalid_single_todoitem_returns_404(self):
        """Get single record that does not exist"""
        response = client.get(
            reverse("todolist:todoitemsingle", kwargs={"name": "invalid"})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PostSingleToDoItemTest(ToDoItemViewTestBase):
    """Test module for POST single todoitem API"""

    def setUp(self):
        self.init_db()
        # Add one more to-do item with a non-consecutive priority
        name = "FifthItem"
        self.records[name] = ToDoItem.objects.create(
            name=name,
            description="Fifth todo item",
            to_do_list=self.to_do_list,
            priority=5,
        )

    def test_post_valid_todoitem_inserts_it(self):
        """Posting a valid record with an unused name inserts it"""

        test_name = "FourthItem"
        valid_payload = {
            "name": test_name,
            "description": "Fourth to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 4,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
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
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_post_valid_todoitem_matching_priority_moves_other_items(self):
        """
        Posting a valid record with an already used priority moves other items downward in
        priority to make room
        """

        test_name = "FourthItem"
        valid_payload = {
            "name": test_name,
            "description": "Fourth to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 2,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results to account for the priority change
        self.records["SecondItem"].priority = 3
        self.records["ThirdItem"].priority = 4

        expected_results = copy(
            ToDoItemSerializer(self.records.values(), many=True).data
        )
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        # Insert the newly created record in the correct spot
        expected_results.insert(1, valid_payload)

        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the record for the other list from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(self.other_list_item)
        test_record = ToDoItem.objects.get(name=self.other_list_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_post_valid_todoitem_diff_list_same_priority_inserts_it(self):
        """
        Posting a valid record with the same priority as another item, but in a different
        list, works and does not alter the original item
        """
        test_name = "FourthItem"
        existing_item = self.records["SecondItem"]
        valid_payload = {
            "name": test_name,
            "description": "Test to do item",
            "to_do_list": self.other_to_do_list.name,
            "priority": existing_item.priority,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
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
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

        # Fetch the other record from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(existing_item)
        test_record = ToDoItem.objects.get(name=existing_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_post_invalid_todoitem_returns_400(self):
        """Posting an invalid record returns a 400"""

        invalid_payload = {
            "name": "",
            "description": "Invalid to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 4,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_duplicate_todoitem_name_returns_400(self):
        """Posting a record with a name already in use returns a 400"""

        test_name = self.records["SecondItem"].name
        invalid_payload = {
            "name": test_name,
            "description": "Invalid to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 4,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Validate that the duplicate record was not inserted. Can't use get()
        # here since it will raise if the insert succeeded
        records = ToDoItem.objects.filter(name=test_name)
        self.assertEqual(len(records), 1)

    def test_post_nonexistent_todolist_returns_400(self):
        """Posting a record for a todolist which does not exist returns a 400"""

        test_name = "Invalid_item"
        invalid_payload = {
            "name": test_name,
            "description": "Invalid to do item",
            "to_do_list": "I_do_not_exist",
            "priority": 4,
        }
        response = client.post(
            reverse("todolist:todoitemmult"),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Validate that the invalid record was not inserted. Can't use get()
        # here since it will raise if the insert succeeded
        records = ToDoItem.objects.filter(name=test_name)
        self.assertEqual(len(records), 0)


class PutSingleToDoItemTest(ToDoItemViewTestBase):
    """Test module for PUT single todoitem API"""

    def setUp(self):
        self.init_db()

    def test_put_valid_todoitem_unused_priority_updates_it(self):
        """Updating a valid record with valid data and an unused priority updatess it"""

        test_name = self.records["SecondItem"].name
        valid_payload = {
            "name": test_name,
            "description": "Still the second to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 4,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
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
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_put_valid_todoitem_used_priority_higher_updates_it(self):
        """
        Updating a valid record with valid data and a used priority hgiher in the list
        moves other items to make room and then updatess it. Note that one of the moved
        items may take the priority the item had before being upaated.
        """

        test_name = self.records["SecondItem"].name
        valid_payload = {
            "name": test_name,
            "description": self.records["SecondItem"].description,
            "to_do_list": self.to_do_list.name,
            "priority": 1,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["SecondItem"].priority = 1
        self.records["FirstItem"].priority = 2
        expected_records = [
            self.records["SecondItem"],
            self.records["FirstItem"],
            self.records["ThirdItem"],
        ]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)
        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the record for the other list from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(self.other_list_item)
        test_record = ToDoItem.objects.get(name=self.other_list_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_put_valid_todoitem_used_priority_lower_updates_it(self):
        """
        Updating a valid record with valid data and a used priority lower in the list
        moves other items to make room and then updatess it.
        """

        test_name = self.records["FirstItem"].name
        valid_payload = {
            "name": test_name,
            "description": self.records["FirstItem"].description,
            "to_do_list": self.to_do_list.name,
            "priority": 3,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["ThirdItem"].priority = 4
        self.records["FirstItem"].priority = 3
        expected_records = [
            self.records["SecondItem"],
            self.records["FirstItem"],
            self.records["ThirdItem"],
        ]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the record for the other list from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(self.other_list_item)
        test_record = ToDoItem.objects.get(name=self.other_list_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_put_valid_todoitem_change_valid_list_unused_priority_updates_it(self):
        """
        Updating a valid todo item to move it to a new todo list with an unused priority
        updatess it
        """

        test_name = self.records["SecondItem"].name
        valid_payload = {
            "name": test_name,
            "description": "Second to do item",
            "to_do_list": self.other_to_do_list.name,
            "priority": 2,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
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
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_put_valid_todoitem_change_valid_list_used_priority_moves_priorities(self):
        """
        Updating a valid record with valid data to change todo lists, such that its priority
        is already in use, lowers the priority of existing items to make room and then updates it
        """

        test_name = self.records["FirstItem"].name
        valid_payload = {
            "name": test_name,
            "description": self.records["FirstItem"].description,
            "to_do_list": self.other_to_do_list.name,
            "priority": 1,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["FirstItem"].to_do_list = self.other_to_do_list
        self.other_list_item.priority = 2
        expected_records = [self.records["FirstItem"], self.other_list_item]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        actual_records = ToDoItem.objects.filter(to_do_list=self.other_to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the records remaining in the original todo list from the DB and validate
        # they were not altered
        expected_records = [self.records["SecondItem"], self.records["ThirdItem"]]
        expected_results = ToDoItemSerializer(expected_records, many=True).data
        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = ToDoItemSerializer(actual_records, many=True).data
        self.assertEqual(expected_results, actual_results)

    def test_put_change_todoitem_name_returns_400(self):
        """Attempting to update the toditem name returns an error"""

        old_name = self.records["SecondItem"].name
        new_name = "InvalidItem"
        invalid_payload = {
            "name": new_name,
            "description": "Invalid to do item",
            "to_do_list": self.to_do_list.name,
            "priority": 2,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": old_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Since 'name' is the primary key, a successful DB update would have duplicated
        # the existing record with the new primary key value. Validate that one does
        # NOT exist. Can't use get() here since it will raise if the record does not exist
        records = ToDoItem.objects.filter(name=new_name)
        self.assertEqual(len(records), 0)

    def test_put_change_todoitem_invalid_list_returns_400(self):
        """
        Attempting to update the todo item to move it to a todo list which does not
        exist returns an error
        """

        test_name = self.records["SecondItem"].name
        invalid_payload = {
            "name": test_name,
            "description": "Invalid to do item",
            "to_do_list": "I_do_not_exist",
            "priority": 2,
        }
        response = client.put(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Fetch the record and ensure it is still in the orignal todo list
        record = ToDoItem.objects.get(name=test_name)
        self.assertEqual(self.records["SecondItem"].to_do_list, record.to_do_list)


class PatchSingleToDoItemTest(ToDoItemViewTestBase):
    """Test module for PATCH single todoitem API"""

    def setUp(self):
        self.init_db()

    def test_patch_valid_todoitem_no_todo_list_no_priority_updates_it(self):
        """
        Updating a valid record with valid data that does not include a todo list or
        priority updatess it
        """

        test_name = self.records["SecondItem"].name
        valid_payload = {"description": "Still the second to do item"}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
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
        expected_results["to_do_list"] = self.records["SecondItem"].to_do_list.name
        expected_results["priority"] = self.records["SecondItem"].priority
        self.assertEqual(returned_data, expected_results)

        # Fetch the record from the DB and validate it was updated
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_patch_valid_todoitem_used_priority_higher_updates_it(self):
        """
        Updating a valid record with valid data and a used priority hgiher in the list
        moves other items to make room and then updatess it. Note that one of the moved
        items may take the priority the item had before being upaated.
        """

        test_name = self.records["SecondItem"].name
        valid_payload = {"priority": 1}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        # Inject the data for fields not included in the patch
        valid_payload["name"] = self.records["SecondItem"].name
        valid_payload["description"] = self.records["SecondItem"].description
        valid_payload["to_do_list"] = self.records["SecondItem"].to_do_list.name
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["SecondItem"].priority = 1
        self.records["FirstItem"].priority = 2
        expected_records = [
            self.records["SecondItem"],
            self.records["FirstItem"],
            self.records["ThirdItem"],
        ]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the record for the other list from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(self.other_list_item)
        test_record = ToDoItem.objects.get(name=self.other_list_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_patch_valid_todoitem_used_priority_lower_updates_it(self):
        """
        Updating a valid record with valid data and a used priority lower in the list
        moves other items to make room and then updatess it.
        """

        test_name = self.records["FirstItem"].name
        valid_payload = {"priority": 3}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Creating the record set timestamp fields. To get a stable test,
        # strip them before doing the comparision
        returned_data = copy(response.data)
        strip_timestamps(returned_data)
        # Inject the data for fields not included in the patch
        valid_payload["name"] = self.records["FirstItem"].name
        valid_payload["description"] = self.records["FirstItem"].description
        valid_payload["to_do_list"] = self.records["FirstItem"].to_do_list.name
        self.assertEqual(returned_data, valid_payload)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["ThirdItem"].priority = 4
        self.records["FirstItem"].priority = 3
        expected_records = [
            self.records["SecondItem"],
            self.records["FirstItem"],
            self.records["ThirdItem"],
        ]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the record for the other list from the DB and validate it was not altered
        expected_serializer = ToDoItemSerializer(self.other_list_item)
        test_record = ToDoItem.objects.get(name=self.other_list_item.name)
        actual_serializer = ToDoItemSerializer(test_record)
        self.assertEqual(expected_serializer.data, actual_serializer.data)

    def test_patch_change_todoitem_name_returns_400(self):
        """Attempting to update the toditem name returns an error"""

        old_name = self.records["SecondItem"].name
        new_name = "InvalidItem"
        invalid_payload = {"name": new_name}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": old_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Since 'name' is the primary key, a successful DB update would have duplicated
        # the existing record with the new primary key value. Validate that one does
        # NOT exist. Can't use get() here since it will raise if the record does not exist
        records = ToDoItem.objects.filter(name=new_name)
        self.assertEqual(len(records), 0)

    def test_patch_valid_todoitem_change_list_unused_priority_updates_it(self):
        """
        Updating a valid record with a new valid todo list where its current
        priority is unused updatess it
        """

        test_name = self.records["SecondItem"].name
        valid_payload = {"to_do_list": self.other_to_do_list.name}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
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
        expected_results["description"] = self.records["SecondItem"].description
        expected_results["priority"] = self.records["SecondItem"].priority
        self.assertEqual(returned_data, expected_results)

        # Fetch the record from the DB and validate it was updated
        test_record = ToDoItem.objects.get(name=test_name)
        serializer = ToDoItemSerializer(test_record)
        self.assertEqual(response.data, serializer.data)

    def test_patch_valid_todoitem_change_valid_list_used_priority_moves_priorities(
        self,
    ):
        """
        Updating a valid record with valid data to change todo lists, such that its priority
        is already in use, lowers the priority of existing items to make room and then updates it
        """

        test_name = self.records["FirstItem"].name
        valid_payload = {"to_do_list": self.other_to_do_list.name}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
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
        expected_results["description"] = self.records["FirstItem"].description
        expected_results["priority"] = self.records["FirstItem"].priority
        self.assertEqual(returned_data, expected_results)

        # Fetch all records for the todo list and ensure they are correct.
        # Update the stored results, and the ordering,  to account for the
        # priority change
        self.records["FirstItem"].to_do_list = self.other_to_do_list
        self.other_list_item.priority = 2
        expected_records = [self.records["FirstItem"], self.other_list_item]
        expected_results = copy(ToDoItemSerializer(expected_records, many=True).data)
        # The records have timestamp fields, which may have been updated if the priority was
        # changed. To get a stable test, strip them before the comparision
        for result in expected_results:
            strip_timestamps(result)

        actual_records = ToDoItem.objects.filter(to_do_list=self.other_to_do_list)
        actual_results = copy(ToDoItemSerializer(actual_records, many=True).data)
        for result in actual_results:
            strip_timestamps(result)
        self.assertEqual(expected_results, actual_results)

        # Fetch the records remaining in the original todo list from the DB and
        # validate they were not altered
        expected_records = [self.records["SecondItem"], self.records["ThirdItem"]]
        expected_results = ToDoItemSerializer(expected_records, many=True).data
        actual_records = ToDoItem.objects.filter(to_do_list=self.to_do_list)
        actual_results = ToDoItemSerializer(actual_records, many=True).data
        self.assertEqual(expected_results, actual_results)

    def test_patch_change_todoitem_invalid_list_returns_400(self):
        """
        Attempting to update the todo item to move it to a todo list which does not
        exist returns an error
        """

        test_name = self.records["SecondItem"].name
        invalid_payload = {"to_do_list": "I_do_not_exist"}
        response = client.patch(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name}),
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Fetch the record and ensure it is still in the orignal todo list
        record = ToDoItem.objects.get(name=test_name)
        self.assertEqual(self.records["SecondItem"].to_do_list, record.to_do_list)


class DeleteSingleToDoItemTest(ToDoItemViewTestBase):
    """Test module for DELETE single todoitem API"""

    def setUp(self):
        self.init_db()

    def test_delete_valid_todoitem_removes_it(self):
        """Deleting a valid record removes it"""

        test_name = self.records["SecondItem"].name
        response = client.delete(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

        # Fetch the record from the DB and validate it no longer exists. Can't
        # use get() here since it will raise if the record does not exist
        records = ToDoItem.objects.filter(name=test_name)
        self.assertEqual(len(records), 0)

    def test_delete_non_existent_name_returns_404(self):
        """Attempting to delete a non-existent toditem returns an error"""

        test_name = "InvalidItem"
        response = client.delete(
            reverse("todolist:todoitemsingle", kwargs={"name": test_name})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
