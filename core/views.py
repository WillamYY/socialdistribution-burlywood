from django.shortcuts import render, redirect, get_object_or_404
from .models import Author
from django.http import HttpResponse
from .forms import AuthorProfileForm

# Create your views here.
def SignUpView(request):
    if request.method == "GET": # Can't post to the website
        return render(request,"signup.html")

# Processes new signups
def SignUpProcessing(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        github = request.POST.get("github", "")
        picture = request.FILES.get("picture", None)

        if Author.objects.filter(username=username).count() == 0:
            new_author = Author(
                username=username,
                password=password,
                name=name,
                description=description,
                github=github,
                picture=picture
            )
            new_author.save()
    return redirect("SignUp")

# Login view
def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        try:
            author = Author.objects.get(username=username, password=password)
            # Store the logged-in author in session
            request.session['author_id'] = author.id
            request.session['username'] = author.username
            return redirect('/app/profile')

        except Author.DoesNotExist:
            error = "Invalid credentials"
            return render(request, "login.html", {"error": error})
    return render(request, "login.html")


# Logout view
def logout_view(request):
    request.session.flush()
    return redirect('/app/login')

# Edit Profile view
def edit_profile(request):
    if not request.session.get('author_id'):
        return redirect('/app/login')

    author = Author.objects.get(id=request.session['author_id'])

    if request.method == "POST":
        # Update username safely
        new_username = request.POST.get('username')
        if new_username and new_username != author.username:
            if Author.objects.filter(username=new_username).exists():
                error = "Username already taken"
                return render(request, "edit_profile.html", {"author": author, "error": error})
            author.username = new_username
            request.session['username'] = new_username  # Update session username

        # Update other fields
        author.name = request.POST.get('name')
        author.description = request.POST.get('description')
        author.github = request.POST.get('github')

        if request.FILES.get('picture'):
            author.picture = request.FILES['picture']

        author.save()
        success = "Profile updated successfully!"
        return render(request, "edit_profile.html", {"author": author, "success": success})

    return render(request, "edit_profile.html", {"author": author})

def profile_view(request):
    if not request.session.get('author_id'):
        return redirect('/app/login')

    author = Author.objects.get(id=request.session['author_id'])
    return render(request, "profile.html", {"author": author})
