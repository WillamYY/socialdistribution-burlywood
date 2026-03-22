from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('like/<uuid:entry_id>/', views.add_like, name='add_like'),
    path('comment/<uuid:entry_id>/', views.add_comment, name='add_comment'),
    path('like-comment/<uuid:comment_id>/', views.add_comment_like, name='add_comment_like'),
    #path('remote/like/<path:entry_id>', views.add_remote_like, name='add_remote_like'),
    path("like-remote/<path:entry_id>/", views.add_remote_like, name="add_remote_like"),
    path("comment-remote/<path:entry_id>/", views.add_remote_comment, name="add_remote_comment"),
]