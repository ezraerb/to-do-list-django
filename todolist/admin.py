""" Register todo list models so they can be manipulated through the Django admin interface """
from django.contrib import admin

from .models import ToDoList, ToDoItem

admin.site.register(ToDoList)
admin.site.register(ToDoItem)
