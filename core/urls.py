from django.urls import path
from . import views

# Specifies the url patterns for all in the core of the project
urlpatterns = [
    path("signup",views.SignUpView,name="SignUp"),
    path("proccess-signup",views.SignUpProcessing,name="SignUpProcessing"),
    path("login", views.login_view, name="Login"),
    path("logout", views.logout_view, name="Logout"),
    path("edit-profile", views.edit_profile, name="EditProfileView"),
    path("profile", views.profile_view, name="ProfileView"),

]