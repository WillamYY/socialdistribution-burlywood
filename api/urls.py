from django.urls import path
from . import views
from django.contrib import admin

# Specifies the url patterns for all in the api of the project
urlpatterns = [
    path("authors/",views.ApiAuthors,name="ApiAuthors"),
    path("authors/<int:id>/",views.ApiAuthor,name="ApiAuthor")
]