from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author, AuthorRequest
from django.contrib.auth.hashers import check_password


def SignUpView(request):
    """
    Displays the signup form.
    Also collects and shows any error messages from previous attempts.
    """
    message_string = ""
    for message in messages.get_messages(request):
        message_string += message.message
    return render(request, "signup.html", {"message": message_string})

def SignUpProcessing(request):
    """
    Handles form submission for signup.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        #name = request.POST.get("name", "")
        #description = request.POST.get("description", "")
        #github = request.POST.get("github", "")
        #picture = request.FILES.get("picture", None)

        # Ensures the username is not taken and that it isn't currently pending in an author request
        if not Author.objects.filter(username=username).exists() and not AuthorRequest.objects.filter(username=username).exists():
            new_author = AuthorRequest(
                username=username,
                #name=name,
                #description=description,
                #github=github,
                #picture=picture
                password = password
            )
            #new_author.set_password(password)  # hash password
            new_author.save()
            messages.info(request,"Approval Pending") # Tells the user that the approval for siging up is pending
            return redirect("SignUp")
        else:
            messages.error(request, "Username already taken")
            return redirect("SignUp")
    return redirect("SignUp")

def NodeDisplay(request):
    """
    Displays all authors in the node.
    """
    node_authors = Author.objects.all()
    return render(request, "node.html", {"users": node_authors})

def ProfileDisplay(request, id):
    """
    Displays a public profile page for any author given their id.
    """
    author = get_object_or_404(Author, pk=id)
    return render(request, "profileview.html", {"username": author.username})

def login_view(request):
    """
    Handles login for both plain text (legacy) and hashed passwords (signup users).
    """
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            author = Author.objects.get(username=username)
            # Check both hashed and plain text passwords
            if check_password(password, author.password) or author.password == password:
                request.session['author_id'] = author.id
                request.session['username'] = author.username
                return redirect('/app/profile')  # or NodeDisplay
            else:
                error = "Invalid username or password"
        except Author.DoesNotExist:
            error = "Invalid username or password"

    return render(request, "login.html", {"error": error})

def logout_view(request):
    """
    Logs out the current user by clearing the session.
    Redirects to login page.
    """
    request.session.flush()
    return redirect("/app/login")

def edit_profile(request):
    """
    Allows the logged-in author to edit their profile
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])

    if request.method == "POST":
        new_username = request.POST.get("username")
        if new_username and new_username != author.username:
            if Author.objects.filter(username=new_username).exists():
                error = "Username already taken"
                return render(request, "edit_profile.html", {"author": author, "error": error})
            author.username = new_username
            request.session["username"] = new_username

        author.name = request.POST.get("name")
        author.description = request.POST.get("description")
        author.github = request.POST.get("github")

        if request.FILES.get("picture"):
            author.picture = request.FILES["picture"]

        author.save()
        success = "Profile updated successfully!"
        return render(request, "edit_profile.html", {"author": author, "success": success})

    return render(request, "edit_profile.html", {"author": author})

def profile_view(request):
    """
    Displays the profile page for the currently logged-in author.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])
    return render(request, "profile.html", {"author": author})

def ProfileDisplay(request, id):
    author = get_object_or_404(Author, pk=id)
    return render(request, "profileview.html", {"author": author})