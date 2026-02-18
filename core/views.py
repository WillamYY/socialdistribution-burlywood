from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author

"""
Displays the signup form
"""
def SignUpView(request):
    # Handles error messages
    error_string = ""
    for error in messages.get_messages(request):
        error_string += error.message
    return render(request,"signup.html",{"errormessage":error_string})
"""
Handles the sign up from the info of the form
"""
def SignUpProcessing(request):
    if request.method == "POST":
        # Gets the username and password from the post request
        username = request.POST["username"]
        password = request.POST["password"]
        if Author.objects.filter(username=username).count() == 0: # Prevents reusing username
            # Gets the new author
            new_author = Author(username = username,password = password)
            new_author.save()
            return redirect("NodeDisplay") # Redirects to inside the node once sign up successful
        else:
            messages.error(request,"Username already taken")
    return redirect("SignUp") # Redirects back to signup, change later



"""
Displays the signin form
"""
def SignInView(request):
    # Handles error messages
    error_string = ""
    for error in messages.get_messages(request):
        error_string += error.message
    return render(request,"signin.html",{"errormessage":error_string})
"""
Handles Signing in
"""
def SignInProcessing(request):
    if request.method == "POST":
        # Gets the username and password from the post request
        username = request.POST["username"]
        password = request.POST["password"]
        if Author.objects.filter(username=username,password = password).count() != 0: # Checks if the username and password is a match for the node
            return redirect("NodeDisplay") # Redirects to inside the node once sign up successful
        else:
            messages.error(request,"Username or password incorrect")
    return redirect("SignIn") # Redirects back to signup, change later



"""
Shows the inside of a node
"""
def NodeDisplay(request):
    node_authors = Author.objects.all()
    return render(request,"node.html",{"users": node_authors})
"""
Handles displaying the user profile page
"""
def ProfileDisplay(request,username):
    # Ensures the user exists
    if Author.objects.filter(username = username):
        # Renders the authors information
        return render(request,"profileview.html",{"username": username})
    # Renders and error message if the user does not exist
    else:
        return render(request,"error.html",{"errormessage": "User does not exist"})