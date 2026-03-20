from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author, FollowRequest, AuthorRequest, IncomingNode, RemoteFollow, RemoteFollowRequest, RemoteFollower
from entries.models import Entry
from interactions.models import Like, Comment
from django.contrib.auth.hashers import check_password
from django.urls import reverse, resolve, Resolver404
from .services import sync_author_github_activity
from .validators import validate_username, validate_password, validate_github_url
import requests
import json
from api.serializers import EntrySerializer
import re

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
    Validates username, password, and account type.
    """
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        account_type = request.POST.get("account_type", "author")

        # Validate username format
        ok, err = validate_username(username)
        if not ok:
            messages.error(request, err)
            return redirect("SignUp")

        # Validate password
        ok, err = validate_password(password)
        if not ok:
            messages.error(request, err)
            return redirect("SignUp")

        # Check username availability
        if Author.objects.filter(username=username).exists() or AuthorRequest.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("SignUp")

        new_author = AuthorRequest(
            username=username,
            name=username,
            host=f"http://{request.get_host()}/api",
            password=password,
        )
        new_author.save()
        messages.info(request, "Approval Pending")
        return redirect("SignUp")
    return redirect("SignUp")

def NodeDisplay(request):
    """
    Displays all authors in the node.
    """
    node_authors = Author.objects.all()
    other_node_authors = []
    # Gets authors from other nodes
    for node in IncomingNode.objects.all():
        resp = requests.get(node.url.rstrip("/") + "/api/authors/", timeout=10)
        if resp.status_code != 200:
            continue
        data = resp.json()
        authors = data.get("authors") or []
        if not isinstance(authors, list):
            continue
        base = node.url.rstrip("/")
        for author in authors:
            if not isinstance(author, dict):
                continue
            aid = author.get("id")
            if aid and not str(aid).startswith("http"):
                author = dict(author)
                author["id"] = f"{base}/api/authors/{aid}"
            other_node_authors.append(author)
    return render(request, "node.html", {"users": node_authors,"other_users":other_node_authors})

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
                return redirect('/app/profile')
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
    Validates username format, uniqueness, and GitHub URL.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])

    if request.method == "POST":
        new_username = (request.POST.get("username") or "").strip()
        github = (request.POST.get("github") or "").strip()
        author.name = request.POST.get("name", author.name)
        author.description = request.POST.get("description", author.description)
        author.github = github

        if new_username:
            ok, err = validate_username(new_username)
            if not ok:
                author.username = new_username
                return render(request, "edit_profile.html", {"author": author, "error": err})

        if new_username and new_username != author.username:
            if Author.objects.filter(username=new_username).exists():
                author.username = new_username
                return render(request, "edit_profile.html", {"author": author, "error": "Username already taken"})
            author.username = new_username
            request.session["username"] = new_username

        ok, err = validate_github_url(github)
        if not ok:
            return render(request, "edit_profile.html", {"author": author, "error": err})

        author.github = github if github else ""

        if request.FILES.get("picture"):
            author.picture = request.FILES["picture"]

        author.save()

        if author.github:
            synced, _ = sync_author_github_activity(author)
            success = "Profile updated successfully!"
            if synced:
                success += f" Synced {synced} new GitHub activity."
        else:
            success = "Profile updated successfully!"
        return render(request, "edit_profile.html", {"author": author, "success": success})

    return render(request, "edit_profile.html", {"author": author})

def sync_github_view(request):
    """
    Sync the logged-in author's GitHub public activity into public entries.
    User Story #5.
    """
    if not request.session.get('author_id'):
        return redirect('/app/login/')

    author = get_object_or_404(Author, id=request.session['author_id'])
    created, err = sync_author_github_activity(author)
    if err:
        messages.warning(request, err)
    else:
        messages.success(request, f'Synced {created} new GitHub activity as public entries.')
    return redirect('ProfileView')


def profile_view(request):
    """
    Displays the profile of the logged-in user.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])

    followers_count = author.followers.exclude(id__in=author.following.values_list("id", flat=True)).count()
    following_count = author.following.exclude(id__in=author.followers.values_list("id", flat=True)).count()
    friends_count = author.friends().count()
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
    public_entries = Entry.objects.filter(author=author, visibility="PUBLIC")
    base_url = request.build_absolute_uri('/')[:-1]
    for entry in public_entries:
        entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        entry.like_count = Like.objects.filter(object=entry_url).count()
        entry.comment_count = Comment.objects.filter(entry=entry_url).count()
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
        if target in me.following.all():
            messages.info(request, f"You are already following {target.username}.")
        elif FollowRequest.objects.filter(requester=me, target=target).exists():
            messages.info(request, "Follow request already sent.")
        else:
            FollowRequest.objects.create(requester=me, target=target)
            messages.success(request, f"Follow request sent to {target.username}!", extra_tags='follow')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        try:
            base_url = request.build_absolute_uri('/')[:-1]
            match = resolve(referer.replace(base_url, ""))
            list_views = ["ProfileDisplay", "connections"]
            if match.url_name in list_views:
                request.session['last_feed_url'] = referer
        except (Resolver404, ValueError):
            pass

    return_url = request.session.get('last_feed_url', f'/app/user/{author_id}/')
    return redirect(return_url)

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

    referer = request.META.get('HTTP_REFERER')
    if referer:
        try:
            base_url = request.build_absolute_uri('/')[:-1]
            match = resolve(referer.replace(base_url, ""))
            list_views = ["ProfileDisplay", "connections"]
            if match.url_name in list_views:
                request.session['last_feed_url'] = referer
        except (Resolver404, ValueError):
            pass

    return_url = request.session.get('last_feed_url', f'/app/user/{author_id}/')
    return redirect(return_url)

def view_follow_requests(request):
    """
    Shows all pending follow requests for the logged-in author.
    Includes both local (FollowRequest) and remote (RemoteFollowRequest).
    """
    author_id = request.session.get('author_id')
    if not author_id:
        return redirect('/app/login')

    author = get_object_or_404(Author, id=author_id)
    requests = FollowRequest.objects.filter(target=author)
    remote_requests = RemoteFollowRequest.objects.filter(target=author)

    return render(request, 'follow_request.html', {
        'author': author,
        'requests': requests,
        'remote_requests': remote_requests,
    })

def approve_follow(request, req_id):
    """
    Approves a follow request.
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


def approve_remote_follow(request, req_id):
    """Approves a follow request from a remote actor. Records RemoteFollower for friends logic."""
    remote_req = get_object_or_404(RemoteFollowRequest, id=req_id, target_id=request.session.get('author_id'))
    name = remote_req.actor_display_name or "Remote author"
    actor_fqid = remote_req.actor_fqid
    target = remote_req.target
    remote_req.delete()
    # Record that this remote actor follows us (for friends = mutual follow logic)
    RemoteFollower.objects.get_or_create(actor_fqid=actor_fqid, target=target)
    messages.success(request, f"You approved {name}'s follow request!", extra_tags='follow')
    return redirect('view_follow_requests')


def deny_remote_follow(request, req_id):
    """Denies a follow request from a remote actor."""
    remote_req = get_object_or_404(RemoteFollowRequest, id=req_id, target_id=request.session.get('author_id'))
    remote_req.delete()
    messages.info(request, "Request denied.", extra_tags='follow')
    return redirect('view_follow_requests')

def connections(request):
    author_id = request.session.get('author_id')
    if not author_id:
        return redirect('/app/login')
    author = get_object_or_404(Author, id=author_id)

    followers = author.followers.exclude(id__in=author.following.values_list("id", flat=True))
    for follower in followers:
        follower.request_sent = FollowRequest.objects.filter(requester=author, target=follower).exists()

    followings = author.following.exclude(id__in=author.followers.values_list("id", flat=True))
    friends = author.friends()
    remote_followings = list(
        RemoteFollow.objects.filter(follower=author).order_by("created_at")
    )

    return render(request, "connections.html", {
        "followers": followers,
        "followings": followings,
        "friends": friends,
        "remote_followings": remote_followings,
    })


def _normalize_fqid(s):
    """Normalize author FQID for storage/comparison."""
    if not s:
        return ""
    s = str(s).strip().rstrip("/")
    if s.startswith("http://"):
        s = "https" + s[4:]
    return s


def follow_remote_author(request, fqid):
    """
    Follow a remote author. POSTs Follow to their inbox and stores RemoteFollow locally.
    Same UI flow as follow_author for local authors.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    me = Author.objects.get(id=request.session["author_id"])
    normalized = _normalize_fqid(fqid)
    if not normalized:
        messages.error(request, "Invalid author.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    if RemoteFollow.objects.filter(follower=me, followed_fqid=normalized).exists():
        messages.info(request, "You are already following this author.")
    else:
        RemoteFollow.objects.create(follower=me, followed_fqid=normalized)
        try:
            base = request.build_absolute_uri("/")[:-1]
            author_base = me.host.rstrip("/") if me.host else base
            if "/api" not in author_base:
                author_base = f"{author_base.rstrip('/')}/api"
            actor_id = f"{author_base}/authors/{me.id}"
            actor_info = {
                "type": "author",
                "id": actor_id,
                "host": author_base,
                "displayName": me.name or me.username,
                "github": me.github or "",
                "profileImage": getattr(me, "picture_url", None) or "",
                "web": me.web or "",
            }
            object_info = {"type": "author", "id": normalized}
            inbox_url = f"{normalized.rstrip('/')}/inbox"
            requests.post(
                inbox_url,
                json={"type": "follow", "actor": actor_info, "object": object_info},
                timeout=10,
            )
        except Exception:
            pass
        messages.success(request, "Follow request sent!", extra_tags="follow")

    referer = request.META.get("HTTP_REFERER")
    if referer:
        try:
            base_url = request.build_absolute_uri("/")[:-1]
            match = resolve(referer.replace(base_url, ""))
            if match.url_name in ("ProfileDisplay", "RemoteProfileDisplay", "connections"):
                request.session["last_feed_url"] = referer
        except (Resolver404, ValueError):
            pass
    return redirect(request.session.get("last_feed_url", referer or "/"))


def unfollow_remote_author(request, fqid):
    """
    Unfollow a remote author. Same UI flow as unfollow_author for local authors.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    me = Author.objects.get(id=request.session["author_id"])
    normalized = _normalize_fqid(fqid)
    RemoteFollow.objects.filter(follower=me, followed_fqid=normalized).delete()
    messages.success(request, "You unfollowed this author.", extra_tags="follow")
    referer = request.META.get("HTTP_REFERER")
    if referer:
        try:
            base_url = request.build_absolute_uri("/")[:-1]
            match = resolve(referer.replace(base_url, ""))
            if match.url_name in ("ProfileDisplay", "RemoteProfileDisplay", "connections"):
                request.session["last_feed_url"] = referer
        except (Resolver404, ValueError):
            pass
    return redirect(request.session.get("last_feed_url", referer or "/"))


def RemoteProfileDisplay(request, fqid):
    """
    Displays the profile of another user.
    """
    is_following = False
    request_sent = False
    logged_in_id = request.session.get("author_id")
    """
    if logged_in_id and Author.objects.filter(id=logged_in_id).exists():
        me = Author.objects.get(id=logged_in_id)
        is_following = author in me.following.all()
        request_sent = FollowRequest.objects.filter(requester=me, target=author).exists()

    user_fqid = None
    if logged_in_id:
        user_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{logged_in_id}"
    public_entries = Entry.objects.filter(author=author, visibility="PUBLIC")
    base_url = request.build_absolute_uri('/')[:-1]
    for entry in public_entries:
        entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        entry.like_count = Like.objects.filter(object=entry_url).count()
        entry.comment_count = Comment.objects.filter(entry=entry_url).count()
        if user_fqid:
            entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
        else:
            entry.liked_by_user = False
    """
    normalized_fqid = _normalize_fqid(fqid)
    is_following = False
    if logged_in_id and normalized_fqid:
        is_following = RemoteFollow.objects.filter(
            follower_id=logged_in_id, followed_fqid=normalized_fqid
        ).exists()

    index = fqid.index("/api/authors/")
    authorInfo = requests.get(fqid[:index] + "/api/authors/" + fqid)
    authorInfo.raise_for_status()
    author = json.loads(authorInfo.text)
    # Gets the authors id
    id = re.search("/api/authors/([^/]*)/?",fqid).group(1)
    entryInfo = requests.get(fqid[:index] + "/api/authors/" + id + "/entries/")
    entryInfo.raise_for_status()
    public_entries = []
    for entry in entryInfo.json().get("src", []):
        if entry["visibility"] == "PUBLIC":
            print(entry["likes"])
            entry["like_count"] = entry["likes"]["count"]
            public_entries.append(entry)
    context = {
        "author": author,
        "followers_count": 0,
        "following_count": 0,
        "is_following": is_following,
        "request_sent": False,
        "logged_in_id": logged_in_id,
        "public_entries": public_entries,
        "author_fqid": normalized_fqid,
    }
    return render(request, "remoteprofileview.html", context) 