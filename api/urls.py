from django.urls import path
from . import views
from django.contrib import admin

#app_name = "api"

# Specifies the url patterns for all in the api of the project
urlpatterns = [
    path("authors/",views.ApiAuthors,name="ApiAuthors"),
    path("authors/<int:id>/",views.ApiAuthor,name="ApiAuthor"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/likes",views.ApiAuthorAndEntryLikes,name="ApiAuthorAndEntryLikes"),
    path("entries/<uuid:entry_id>/likes",views.ApiEntryLikes),
    path("authors/<int:author_id>/inbox",views.ApiSendLike),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/", views.ApiEntry, name="ApiEntry"),
    path("authors/<int:author_id>/entries/", views.ApiEntries, name="ApiEntries"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/image", views.ApiEntryImage, name="ApiEntryImage"),
    path("entries/<uuid:entry_id>/image", views.ApiEntryImage, name="ApiEntryImageGlobal"),
]