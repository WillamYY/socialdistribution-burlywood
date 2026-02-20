from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author
from django.contrib.auth.hashers import make_password, check_password

# --------------------------
# Signup Views
# --------------------------
def SignUpView(request):
    # Handles error messages
    error_string = ""
    for error in messages.get_messages(request):
        error_string += error.message
    return render(request, "signup.html", {"errormessage": error_string})

def SignUpProcessing(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        github = request.POST.get("github", "")
        picture = request.FILES.get("picture", None)

        if Author.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
        else:
            # Store password securely
            new_author = Author(
                username=username,
                password=make_password(password),
                name=name,
                description=description,
                github=github,
                picture=picture
            )
            new_author.save()
            return redirect("NodeDisplay")  # Redirect to Node page

    return redirect("SignUp")

# --------------------------
# Login Views
# --------------------------
def login_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            author = Author.objects.get(username=username)
            if check_password(password, author.password):
                # Login successful
                request.session['author_id'] = author.id
                request.session['username'] = author.username
                return redirect('/app/profile')
            else:
                error = "Invalid username or password"
        except Author.DoesNotExist:
            error = "Invalid username or password"

    return render(request, "login.html", {"error": error})

def logout_view(request):
    request.session.flush()
    return redirect('/app/login')

# --------------------------
# Profile Views
# --------------------------
def profile_view(request):
    if not request.session.get('author_id'):
        return redirect('/app/login')

    author = Author.objects.get(id=request.session['author_id'])
    return render(request, "profile.html", {"author": author})

def edit_profile(request):
    if not request.session.get('author_id'):
        return redirect('/app/login')

    author = Author.objects.get(id=request.session['author_id'])

    if request.method == "POST":
        # Update fields safely
        author.name = request.POST.get('name', author.name)
        author.description = request.POST.get('description', author.description)
        author.github = request.POST.get('github', author.github)

        if request.FILES.get('picture'):
            author.picture = request.FILES['picture']

        author.save()
        success = "Profile updated successfully!"
        return render(request, "edit_profile.html", {"author": author, "success": success})

    return render(request, "edit_profile.html", {"author": author})

# --------------------------
# Node Views
# --------------------------
def NodeDisplay(request):
    node_authors = Author.objects.all()
    return render(request, "node.html", {"users": node_authors})

def ProfileDisplay(request, id):
    try:
        author = Author.objects.get(id=id)
        return render(request, "profileview.html", {"username": author.username})
    except Author.DoesNotExist:
        return render(request, "error.html", {"errormessage": "User does not exist"})