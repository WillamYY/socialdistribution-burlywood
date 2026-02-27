from django.urls import path
from . import views

urlpatterns = [
    path('author/<int:author_id>/entries/<uuid:entry_id>/like/', views.like_entry, name='like_entry'),
    path('author/<int:author_id>/entries/<uuid:entry_id>/comments/create/', views.create_comment, name='create_comment'),
    path('comments/<path:comment_id>/toggle_like/', views.toggle_like_comment, name='toggle_like_comment'),
]
