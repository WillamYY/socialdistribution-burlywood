from django.urls import path
from . import views

urlpatterns = [
    path("authors/<int:author_id>/stream/", views.stream_api, name="stream_api"),
]
