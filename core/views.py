from django.shortcuts import render, redirect
from .models import Author

# Create your views here.
def SignUpView(request):
    if request.method == "GET": # Can't post to the website
        return render(request,"signup.html")

# Processes new signups
def SignUpProcessing(request):
    if request.method == "POST":
        # Gets the username and password from the post request
        username = request.POST["username"]
        password = request.POST["password"]
        if Author.objects.filter(username=username).count() == 0: # Prevents reusing username
            # Gets the new author
            new_author = Author(username = username,password = password)
            new_author.save()
    return redirect("SignUp") # Redirects back to signup, change later