""" Configuration for the todo list application """
from django.apps import AppConfig


class TodolistConfig(AppConfig):
    """Configuration for the todo list application. All defaults except the name"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "todolist"
