from django.urls import path
from . import views

# Specifies the url patterns for all in the core of the project
urlpatterns = [
    path("signup",views.SignUpView,name="SignUp"),
    path("proccess-signup",views.SignUpProcessing,name="SignUpProcessing")
]