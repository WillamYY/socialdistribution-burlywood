from django.urls import path
from . import views
 
urlpatterns = [
    path("", views.NodeDisplay, name="NodeDisplay"),
    path("signup/", views.SignUpView, name="SignUp"),
    path("process-signup/", views.SignUpProcessing, name="SignUpProcessing"),
    path("login/", views.login_view, name="Login"),
    path("logout/", views.logout_view, name="Logout"),
    path("profile/", views.profile_view, name="ProfileView"),
    path("edit-profile/", views.edit_profile, name="EditProfileView"),
    path("user/<int:id>/", views.ProfileDisplay, name="ProfileDisplay"),
    path("user/<int:author_id>/follow/", views.follow_author, name="FollowAuthor"),
    path("user/<int:author_id>/unfollow/", views.unfollow_author, name="UnfollowAuthor"),
    path('follow-requests/', views.view_follow_requests, name='view_follow_requests'),
    path('follow-requests/approve/<int:req_id>/', views.approve_follow, name='ApproveFollow'),
    path('follow-requests/deny/<int:req_id>/', views.deny_follow, name='DenyFollow'),
    path("connections/", views.connections, name="connections")
]
