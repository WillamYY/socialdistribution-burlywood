from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('like/<uuid:entry_id>/', views.add_like, name='add_like'),
    path('comment/<uuid:entry_id>/', views.add_comment, name='add_comment'),
    path('like-comment/<uuid:comment_id>/', views.add_comment_like, name='add_comment_like'),
]