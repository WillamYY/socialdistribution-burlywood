from django.urls import path
from . import views

# Specifies the url patterns for all in the core of the project
urlpatterns = [
    path("<int:id>/",views.NodeDisplay,name="NodeDisplay"),
    # Sign up urls
    path("<int:id>/signup/",views.SignUpView,name="SignUp"),
    path("<int:id>/process-signup/",views.SignUpProcessing,name="SignUpProcessing"),
    # Sign In urls
    path("<int:id>/signin/",views.SignInView,name="SignIn"),
    path("<int:id>/process-signin/",views.SignInProcessing,name="SignInProcessing"),
    # Create node urls
    path("create-node/",views.CreateNodeView,name="CreateNode"),
    path("process-node/",views.CreateNodeProcessing,name="ProcessNode"), # Handles the processing of node creation
    # User profile page
    path("<int:id>/<str:username>/",views.ProfileDisplay,name="ProfileDisplay")
]