from django.urls import path
from . import views

# Specifies the url patterns for all in the core of the project
urlpatterns = [
    path("",views.NodeDisplay,name="NodeDisplay"),
    # Sign up urls
    path("signup/",views.SignUpView,name="SignUp"),
    path("process-signup/",views.SignUpProcessing,name="SignUpProcessing"),
    # Sign In urls
    path("signin/",views.SignInView,name="SignIn"),
    path("process-signin/",views.SignInProcessing,name="SignInProcessing"),
    # User profile page
    path("user/<int:id>/",views.ProfileDisplay,name="ProfileDisplay")
]