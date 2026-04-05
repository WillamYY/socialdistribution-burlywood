from django.urls import path
from . import views
from . import node_admin_views

urlpatterns = [
    path("", views.NodeDisplay, name="NodeDisplay"),
    path("signup/", views.SignUpView, name="SignUp"),
    path("process-signup/", views.SignUpProcessing, name="SignUpProcessing"),
    path("login/", views.login_view, name="Login"),
    path("logout/", views.logout_view, name="Logout"),
    path("node-admin/", node_admin_views.node_admin_dashboard, name="node_admin_dashboard"),
    path(
        "node-admin/my-visibility/",
        node_admin_views.node_admin_set_listed_publicly,
        name="node_admin_set_listed_publicly",
    ),
    path("node-admin/signups/", node_admin_views.node_admin_signups, name="node_admin_signups"),
    path(
        "node-admin/signups/<int:pk>/approve/",
        node_admin_views.node_admin_signup_approve,
        name="node_admin_signup_approve",
    ),
    path(
        "node-admin/signups/<int:pk>/reject/",
        node_admin_views.node_admin_signup_reject,
        name="node_admin_signup_reject",
    ),
    path("node-admin/authors/", node_admin_views.node_admin_authors, name="node_admin_authors"),
    path(
        "node-admin/authors/<int:pk>/delete/",
        node_admin_views.node_admin_author_delete,
        name="node_admin_author_delete",
    ),
    path("node-admin/entries/", node_admin_views.node_admin_entries, name="node_admin_entries"),
    path(
        "node-admin/entries/<uuid:entry_id>/edit/",
        node_admin_views.node_admin_entry_edit,
        name="node_admin_entry_edit",
    ),
    path(
        "node-admin/entries/<uuid:entry_id>/delete/",
        node_admin_views.node_admin_entry_delete,
        name="node_admin_entry_delete",
    ),
    path(
        "node-admin/nodes/incoming/",
        node_admin_views.node_admin_incoming_nodes,
        name="node_admin_incoming_nodes",
    ),
    path(
        "node-admin/nodes/incoming/<int:pk>/delete/",
        node_admin_views.node_admin_incoming_delete,
        name="node_admin_incoming_delete",
    ),
    path(
        "node-admin/nodes/outgoing/",
        node_admin_views.node_admin_outgoing_nodes,
        name="node_admin_outgoing_nodes",
    ),
    path(
        "node-admin/nodes/outgoing/<int:pk>/delete/",
        node_admin_views.node_admin_outgoing_delete,
        name="node_admin_outgoing_delete",
    ),
    path("profile/", views.profile_view, name="ProfileView"),
    path("profile/sync-github/", views.sync_github_view, name="sync_github"),
    path("edit-profile/", views.edit_profile, name="EditProfileView"),
    path("user/<int:id>/", views.ProfileDisplay, name="ProfileDisplay"),
    path("user/<int:author_id>/follow/", views.follow_author, name="FollowAuthor"),
    path("user/<int:author_id>/unfollow/", views.unfollow_author, name="UnfollowAuthor"),
    path('follow-requests/', views.view_follow_requests, name='view_follow_requests'),
    path('follow-requests/approve/<int:req_id>/', views.approve_follow, name='ApproveFollow'),
    path('follow-requests/deny/<int:req_id>/', views.deny_follow, name='DenyFollow'),
    path('follow-requests/approve-remote/<int:req_id>/', views.approve_remote_follow, name='ApproveRemoteFollow'),
    path('follow-requests/deny-remote/<int:req_id>/', views.deny_remote_follow, name='DenyRemoteFollow'),
    path("connections/remove-remote-follower/<path:fqid>/", views.remove_remote_follower, name="RemoveRemoteFollower"),
    path("connections/", views.connections, name="connections"),
    path("hosted-images/<int:image_id>/image/", views.get_admin_hosted_image, name="admin_hosted_image_file"),
    #### URLS FOR REMOTE NODES (more specific first)
    path("user/<path:fqid>/follow/", views.follow_remote_author, name="FollowRemoteAuthor"),
    path("user/<path:fqid>/unfollow/", views.unfollow_remote_author, name="UnfollowRemoteAuthor"),
    path("user/<path:fqid>/", views.RemoteProfileDisplay, name="RemoteProfileDisplay"),
]

