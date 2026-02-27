from django.urls import path
from . import views

urlpatterns = [
    path('create-entry/', views.create_entry, name='create_entry'),
    path('author/<int:author_id>/entries/', views.view_entries, name='view_entries'),
    path('my-entries/', views.view_my_entries, name='view_my_entries'),
    path('edit/<uuid:entry_id>/', views.edit_entry, name='edit_entry'),
    path('delete/<uuid:entry_id>/', views.delete_entry, name='delete_entry'),
    path('authors/<int:author_id>/entries/<uuid:entry_id>/image/', views.get_entry_image, name='get_entry_image'),
    path('author/<int:author_id>/entries/<uuid:entry_id>/like/', views.like_entry, name='like_entry'),
]