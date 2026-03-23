from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from . import views
from django.contrib import admin

app_name = "api"

# Specifies the url patterns for all in the api of the project
urlpatterns = [
    path("authors/", views.ApiAuthors, name="ApiAuthors"),
    path("authors/<int:id>/", views.HandleApiAuthor, name="ApiAuthor"),
    path("authors/<int:author_id>/inbox", csrf_exempt(views.ApiInbox), name="ApiSendLike"),
    path("authors/<int:author_id>/inbox/", csrf_exempt(views.ApiInbox), name="ApiSendLikeSlash"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/likes",views.ApiAuthorAndEntryLikes,name="ApiAuthorAndEntryLikes"),
    path("entries/<path:entry_fqid>/likes",views.ApiEntryLikes, name="ApiEntryLikes"),

    path("authors/<int:author_id>/liked", views.ApiAuthorLiked, name="ApiAuthorLiked"),
    path("authors/<int:author_id>/liked/<uuid:like_id>", views.ApiSingleLikeRemoteLocal, name="ApiSingleLikeRemoteLocal"),
    path("authors/<path:author_fqid>/liked", views.ApiAuthorLikedLocal, name="ApiAuthorLikedLocal"),
    path("liked/<path:like_url>", views.ApiSingleLikeLocal, name="ApiSingleLikeLocal"),
    
    path("authors/<int:author_id>/entries/<uuid:entry_id>", views.ApiEntry, name="ApiEntry"),
    path("entries/<path:entry_fqid>/comments/", views.ApiEntryCommentsByFqid, name="ApiEntryCommentsByFqid"),
    #path("entries/<path:entry_fqid>/", views.ApiEntryGlobal, name="ApiEntryGlobal"),
    path("authors/<int:author_id>/entries/", views.ApiEntries, name="ApiEntries"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/image", views.ApiEntryImage, name="ApiEntryImage"),
    path("entries/<path:entry_fqid>/image", views.ApiEntryImage, name="ApiEntryImageGlobal"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments", views.HandleApiEntryComments, name="ApiEntryCommentsNoSlash"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments/", views.HandleApiEntryComments, name="ApiEntryComments"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments/<path:comment_fqid>/likes/", views.ApiCommentLikes, name="ApiCommentLikes"),
    path("authors/<int:author_id>/entries/<uuid:entry_id>/comments/add/", views.ApiAddComment, name="ApiAddComment"),
    path('entries/public/', views.ApiBrowsePublicEntries, name='browse_public_entries'),
    path("entries/<path:entry_fqid>/", views.ApiEntryByFqid, name="ApiEntryByFqid"),
    # GET author by FQID - last; only matches FQID-style paths (e.g. http%3A%2F%2F...)
    path("authors/<path:author_fqid>/", views.ApiAuthorByFqid, name="ApiAuthorByFqid"),
]