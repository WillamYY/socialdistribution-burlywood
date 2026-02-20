from django.urls import path
from . import views

urlpatterns = [
    path('create-entry/', views.create_entry, name='create_entry'),
    path('my-entries/', views.my_entries, name='my_entries'),
]