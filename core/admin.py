# core/admin.py
from django.contrib import admin
from .models import Author

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'github')  # columns in list
    search_fields = ('username', 'name')          # search box