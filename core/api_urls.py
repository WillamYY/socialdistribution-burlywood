from django.urls import path
from core import api_views

urlpatterns = [
    path('api/authors/<int:author_id>/following/', api_views.api_list_following, name='api-list-following'),
    path('api/authors/<int:author_id>/following/<int:foreign_author_id>/', api_views.api_unfollow_author, name='api-unfollow-author'),
    path('api/authors/<int:author_id>/friends/', api_views.api_list_friends, name='api-list-friends'),
    path('api/authors/<int:author_id>/follow-requests/', api_views.api_list_follow_requests, name='api-list-follow-requests'),
    path('api/follow-requests/approve/<int:req_id>/', api_views.api_approve_follow, name='api-approve-follow'),
    path('api/follow-requests/deny/<int:req_id>/', api_views.api_deny_follow, name='api-deny-follow'),
    path('api/authors/<int:author_id>/follow/', api_views.api_follow_author, name='api-follow-author'),
    path('api/authors/<int:author_id>/profile/', api_views.api_edit_profile, name='api-edit-profile'),
]