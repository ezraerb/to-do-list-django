""" Basic models for a set of todo lists """
from django.db import models


class ToDoList(models.Model):
    """Basic To Do List"""

    name = models.CharField(max_length=25, primary_key=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __repr__(self):
        return self.name + ": " + self.description


class ToDoItem(models.Model):
    """Item on a To Do List"""

    name = models.CharField(max_length=25, primary_key=True)
    description = models.CharField(max_length=255)
    to_do_list = models.ForeignKey(ToDoList, on_delete=models.CASCADE)
    priority = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["to_do_list", "priority"]
        unique_together = ["to_do_list", "priority"]

    def __repr__(self):
        return self.name + ": " + self.description
