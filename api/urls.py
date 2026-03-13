from django.urls import path
from . import views
from django.contrib import admin

app_name = "api"

# Specifies the url patterns for all in the api of the project
urlpatterns = [
    path("authors/",views.ApiAuthors,name="ApiAuthors"),
    path("authors/<int:id>/",views.ApiAuthor,name="ApiAuthor"),
    path("authors/<int:author_id>/inbox",views.ApiSendLike, name="ApiSendLike"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/likes",views.ApiAuthorAndEntryLikes,name="ApiAuthorAndEntryLikes"),
    path("entries/<path:entry_fqid>/likes",views.ApiEntryLikes, name="ApiEntryLikes"),

    path("authors/<int:author_id>/liked", views.ApiAuthorLiked, name="ApiAuthorLiked"),
    path("authors/<int:author_id>/liked/<uuid:like_id>", views.ApiSingleLikeRemoteLocal, name="ApiSingleLikeRemoteLocal"),
    path("authors/<path:author_fqid>/liked", views.ApiAuthorLikedLocal, name="ApiAuthorLikedLocal"),
    path("liked/<path:like_url>", views.ApiSingleLikeLocal, name="ApiSingleLikeLocal"),
    
    path("authors/<int:author_id>/entries/<uuid:entry_id>/", views.ApiEntry, name="ApiEntry"),
    path("authors/<int:author_id>/entries/", views.ApiEntries, name="ApiEntries"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/image", views.ApiEntryImage, name="ApiEntryImage"),
    path("entries/<uuid:entry_id>/image", views.ApiEntryImage, name="ApiEntryImageGlobal"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments/", views.ApiEntryComments, name="ApiEntryComments"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments/add/", views.ApiAddComment, name="ApiAddComment"),
    path('entries/public/', views.ApiBrowsePublicEntries, name='browse_public_entries'),
]