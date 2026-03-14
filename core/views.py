from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author, FollowRequest, AuthorRequest
from entries.models import Entry
from interactions.models import Like
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
            # Ensures the length of the password is at least 8 letters
            if len(password) >= 8:
                # Ensures there is at least one letter and at least one number
                has_letter = False
                has_number = False
                for char in password:
                    if char.isalpha(): # Upon the first letter being found break and note that one was found
                        has_letter = True
                    if char.isnumeric():
                        has_number = True
                    # Once both a letter and number have been found break immediately
                    if has_number and has_letter:
                        break
                if has_letter and has_number:
                    new_author = AuthorRequest(
                        username=username,
                        #name=name,
                        #description=description,
                        #github=github,
                        #picture=picture
                        name=username,
                        host=f"http://{request.get_host()}/",
                        password=password
                    )
                    #new_author.set_password(password)  # hash password
                    new_author.save()
                    messages.info(request,"Approval Pending") # Tells the user that the approval for siging up is pending
                    return redirect("SignUp")
                # Prints an error message if the password is missing both a number and letter
                elif not has_letter and not has_number:
                    messages.error(request,"Password requires at least one letter and one number")
                    return redirect("SignUp")
                # Prints an error message if the password is missing only letter
                elif not has_letter:
                    messages.error(request,"Password requires at least one letter")
                    return redirect("SignUp")
                    # Prints an error message if the password is missing only letter
                elif not has_number:
                    messages.error(request,"Password requires at least one number")
                    return redirect("SignUp")
            # Displays an error message if the password is too short
            else:
                messages.error(request, "Password must be 8 letters")
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

def login_view(request):
    """
    Handles login for both plain text (legacy) and hashed passwords (signup users).
    """
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next") or request.GET.get("next")

        try:
            author = Author.objects.get(username=username)
            # Check both hashed and plain text passwords
            if check_password(password, author.password) or author.password == password:
                request.session['author_id'] = author.id
                request.session['username'] = author.username

                if next_url:
                    return redirect(next_url)
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
    Allows the logged-in author to edit their profile.
    Checks for username uniqueness before updating.
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
    Displays the profile of the logged-in user.
    Shows counts for followers, following, and pending follow requests.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])

    followers_count = author.followers.exclude(id__in=author.following.values_list("id", flat=True)).count()
    following_count = author.following.exclude(id__in=author.followers.values_list("id", flat=True)).count()
    friends_count = author.friends().count()

    # Count pending follow requests for this author
    pending_requests_count = FollowRequest.objects.filter(target=author).count()

    return render(request, "profile.html", {
        "author": author,
        "followers_count": followers_count,
        "following_count": following_count,
        "friends_count": friends_count,
        "pending_requests_count": pending_requests_count
    })

def ProfileDisplay(request, id):
    """
    Displays the profile of another user.
    Checks if the logged-in user is following them or has sent a follow request.
    """
    author = get_object_or_404(Author, pk=id)
    logged_in_id = request.session.get("author_id")
    is_following = False
    request_sent = False

    if logged_in_id and Author.objects.filter(id=logged_in_id).exists():
        me = Author.objects.get(id=logged_in_id)
        is_following = author in me.following.all()
        request_sent = FollowRequest.objects.filter(requester=me, target=author).exists()


    user_fqid = None
    if logged_in_id:
        user_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{logged_in_id}"
    public_entries = Entry.objects.filter(author = author, visibility="PUBLIC")
    base_url = request.build_absolute_uri('/')[:-1]
    for entry in public_entries:
        entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        entry.like_count = Like.objects.filter(object=entry_url).count()

        if user_fqid:
            entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
        else:
            entry.liked_by_user = False

    context = {
        "author": author,
        "followers_count": author.followers.count(),
        "following_count": author.following.count(),
        "is_following": is_following,
        "request_sent": request_sent,
        "logged_in_id": logged_in_id,
        "public_entries": public_entries
    }
    return render(request, "profileview.html", context)

def follow_author(request, author_id):
    """
    Sends a follow request to another author.
    """
    if not request.session.get('author_id'):
        return redirect('/app/login')

    me = Author.objects.get(id=request.session['author_id'])
    target = get_object_or_404(Author, id=author_id)

    if target != me:
        # Check if already following
        if target in me.following.all():
            messages.info(request, f"You are already following {target.username}.")
        # Check if a request already exists
        elif FollowRequest.objects.filter(requester=me, target=target).exists():
            messages.info(request, "Follow request already sent.")
        else:
            # Create a follow request 
            FollowRequest.objects.create(requester=me, target=target)
            messages.success(request, f"Follow request sent to {target.username}!", extra_tags='follow')
    return redirect(f'/app/user/{author_id}/')

def unfollow_author(request, author_id):
    """
    Unfollows a user.
    """
    if not request.session.get('author_id'):
        return redirect('/app/login')

    me = Author.objects.get(id=request.session['author_id'])
    target = get_object_or_404(Author, id=author_id)

    if target != me:
        me.following.remove(target)
        messages.success(request, f"You unfollowed {target.username}.", extra_tags='follow')
    return redirect(f'/app/user/{author_id}/')

def view_follow_requests(request):
    """
    Shows all pending follow requests for the logged-in author.
    """
    author_id = request.session.get('author_id')
    if not author_id:
        return redirect('/app/login')

    author = get_object_or_404(Author, id=author_id)
    requests = FollowRequest.objects.filter(target=author)  # Requests sent to this author

    return render(request, 'follow_request.html', {
        'author': author,
        'requests': requests
    })

def approve_follow(request, req_id):
    """
    Approves a follow request.
    Adds requester to followers of target author and deletes the request.
    """
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.target.followers.add(follow_request.requester)
    follow_request.delete()
    messages.success(request, f"You are now following {follow_request.requester.username}!", extra_tags='follow')
    return redirect('view_follow_requests')

def deny_follow(request, req_id):
    """
    Denies a follow request by deleting it.
    """
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.delete()
    messages.info(request, "Request denied.", extra_tags='follow')
    return redirect('view_follow_requests')

def connections(request):
    author_id = request.session.get('author_id')
    if not author_id:
        return redirect('/app/login')
    author = get_object_or_404(Author, id=author_id)

    # From https://stackoverflow.com/questions/4523282/django-in-not-in-query by Harph
    followers = author.followers.exclude(id__in=author.following.values_list("id", flat=True))
    followings = author.following.exclude(id__in=author.followers.values_list("id", flat=True))
    friends = author.friends()

    return render(request, "connections.html", {
        "followers": followers,
        "followings": followings,
        "friends": friends
    })