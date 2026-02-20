from django.urls import path
from . import views

urlpatterns = [
    path('create-entry/', views.create_entry, name='create_entry'),
    path('author/<int:author_id>/entries/', views.view_entries, name='view_entries'),
]