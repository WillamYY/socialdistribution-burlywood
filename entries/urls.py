from django.urls import include, path
from . import views

urlpatterns = [
    path('stream/', views.stream_view, name='stream'),
    path('create-entry/', views.create_entry, name='create_entry'),
    path('author/<int:author_id>/entries/', views.view_entries, name='view_entries'),
    path('my-entries/', views.view_my_entries, name='view_my_entries'),
    path('edit/<uuid:entry_id>/', views.edit_entry, name='edit_entry'),
    path('delete/<uuid:entry_id>/', views.delete_entry, name='delete_entry'),
    path("entry/<uuid:entry_id>/", views.get_entry, name="get_entry"),

    # Include interactions app logic
    path("interactions/", include("interactions.urls", namespace="interactions")),
]