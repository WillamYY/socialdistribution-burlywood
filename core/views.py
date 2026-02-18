from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author, Node

"""
Displays the signup form
"""
def SignUpView(request,id):
    if Node.objects.filter(id = id).exists():
        # Handles error messages
        error_string = ""
        for error in messages.get_messages(request):
            error_string += error.message
        return render(request,"signup.html",{"errormessage":error_string,"node":id})
    # Renders an error screen if the node being signed up to doesn't exist
    return render(request,"error.html")
"""
Handles the sign up from the info of the form
"""
def SignUpProcessing(request,id):
    if Node.objects.filter(id = id).exists():
        if request.method == "POST":
            # Gets the node that user is signing up to
            node = get_object_or_404(Node,pk=id)
            # Gets the username and password from the post request
            username = request.POST["username"]
            password = request.POST["password"]
            if Author.objects.filter(username=username,node = node).count() == 0: # Prevents reusing username
                # Gets the new author
                new_author = Author(username = username,password = password,node = node)
                new_author.save()
                return redirect("NodeDisplay", id = id) # Redirects to inside the node once sign up successful
            else:
                messages.error(request,"Username already taken")
        return redirect("SignUp",id = id) # Redirects back to signup, change later
    # Renders and error message if the node being signed up to doesn't exist
    else:
        return render(request,"error.html")



"""
Displays the signin form
"""
def SignInView(request,id):
    if Node.objects.filter(id = id).exists():
        # Handles error messages
        error_string = ""
        for error in messages.get_messages(request):
            error_string += error.message
        return render(request,"signin.html",{"errormessage":error_string,"node":id})
    # Renders an error screen if the node being signed up to doesn't exist
    return render(request,"error.html")
"""
Handles Signing in
"""
def SignInProcessing(request,id):
    if Node.objects.filter(id = id).exists():
        if request.method == "POST":
            # Gets the node that user is signing in to
            node = get_object_or_404(Node,pk=id)
            # Gets the username and password from the post request
            username = request.POST["username"]
            password = request.POST["password"]
            if Author.objects.filter(username=username,password = password,node = node).count() != 0: # Checks if the username and password is a match for the node
                return redirect("NodeDisplay", id = id) # Redirects to inside the node once sign up successful
            else:
                messages.error(request,"Username or password incorrect")
        return redirect("SignIn",id = id) # Redirects back to signup, change later
    # Renders and error message if the node being signed up to doesn't exist
    else:
        return render(request,"error.html")



"""
Shows the create node view (Asks for admin username and password)
"""
def CreateNodeView(request):
    # Handles error messages
    error_string = ""
    for error in messages.get_messages(request):
        error_string += error.message + "\n"
    return render(request,"createnode.html",{"errormessage":error_string})
"""
Handles the processing of the creation of a new node
"""
def CreateNodeProcessing(request):
    if request.method == "POST":
        # Creates the admin user
        admin_username = request.POST["username"]
        admin_password = request.POST["password"]
        admin = Author(username = admin_username,password = admin_password)
        admin.save()
        # Creates the new node with admin as one of the authors
        new_node = Node(admin_id = admin.id)
        new_node.save()
        # Adds the node to the admin
        admin.node = new_node
        admin.save()
        return redirect("NodeDisplay", id = id) # Redirects to inside the node once sign up successful
    return redirect("CreateNode")



"""
Shows the inside of a node
"""
def NodeDisplay(request,id):
    if Node.objects.filter(id = id).exists():
        # Gets the node that is being looked at
        node = get_object_or_404(Node,pk=id)
        # Gets all the nodes authors
        node_authors = Author.objects.filter(node = node)
        return render(request,"node.html",{"users": node_authors})
    # Renders and error message if the node being signed up to doesn't exist
    else:
        return render(request,"error.html")
