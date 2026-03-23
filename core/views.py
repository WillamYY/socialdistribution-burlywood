from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author, FollowRequest, AuthorRequest, IncomingNode, RemoteFollow, RemoteFollowRequest, RemoteFollower, AdminHostedImage
from entries.models import Entry
from interactions.models import Like, Comment
from django.contrib.auth.hashers import check_password
from django.urls import reverse, resolve, Resolver404
from .services import sync_author_github_activity
from .validators import validate_username, validate_password, validate_github_url
import requests
import json
import logging
from api.serializers import EntrySerializer
import re
import base64

logger = logging.getLogger(__name__)

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
            host=f"https://{request.get_host()}/api",
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

    return render(request, "node.html", {
        "users": node_authors,
        "other_users": other_node_authors
    })

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

        picture_url = request.POST.get("picture_url", "").strip()
        if picture_url:
            # Accept only URLs ending with common image extensions
            if picture_url.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                author.picture_url = picture_url
            else:
                return render(request, "edit_profile.html", {
                    "author": author,
                    "error": "Please enter a direct image URL ending with .jpg, .jpeg, .png, or .gif"
                })

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

    # Local: followers (excl mutual), following (excl mutual), friends (mutual)
    local_followers_only = author.followers.exclude(id__in=author.following.values_list("id", flat=True))
    local_following_only = author.following.exclude(id__in=author.followers.values_list("id", flat=True))
    local_friends = author.friends()

    # Remote: same logic as connections view
    remote_followings_raw = list(RemoteFollow.objects.filter(follower=author).order_by("created_at"))
    remote_followers_raw = list(RemoteFollower.objects.filter(target=author).order_by("created_at"))
    following_fqids = {_normalize_fqid(rf.followed_fqid) for rf in remote_followings_raw}
    follower_by_fqid = {_normalize_fqid(r.actor_fqid): r for r in remote_followers_raw}
    follower_fqids = set(follower_by_fqid)
    remote_friends = [norm_fqid for norm_fqid in follower_fqids if norm_fqid in following_fqids]
    mutual_fqids = set(remote_friends)
    remote_followings_only = [rf for rf in remote_followings_raw if _normalize_fqid(rf.followed_fqid) not in mutual_fqids]
    remote_followers_only = [r for r in remote_followers_raw if _normalize_fqid(r.actor_fqid) not in mutual_fqids]

    followers_count = local_followers_only.count() + len(remote_followers_only)
    following_count = local_following_only.count() + len(remote_followings_only)
    friends_count = local_friends.count() + len(remote_friends)

    pending_requests_count = FollowRequest.objects.filter(target=author).count()
    pending_requests_count += RemoteFollowRequest.objects.filter(target=author).count()

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
        # Tries both securea and insecure
        if "https" in entry_url:
            alt_url = entry_url.replace("https","http")
        else:
            alt_url = entry_url.replace('http',"https")
        entry.like_count = Like.objects.filter(object=entry_url).count() + Like.objects.filter(object=alt_url).count()
        entry.comment_count = Comment.objects.filter(entry=entry_url).count()
        if user_fqid:
            entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists() or Like.objects.filter(object=alt_url, author=user_fqid).exists()
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


def _send_accept_to_requester(request, actor_fqid, accepter):
    """POST Accept to requester's inbox so their Remote Following updates when we approve."""
    try:
        base = (accepter.host or "").strip().rstrip("/")
        if not base or not base.startswith("http"):
            base = request.build_absolute_uri("/")[:-1]
        if "/api" not in base:
            base = base.rstrip("/") + "/api"
        if base.startswith("http://"):
            base = "https" + base[4:]
        accepter_id = f"{base}/authors/{accepter.id}"
        inbox_url = f"{_normalize_fqid(actor_fqid).rstrip('/')}/inbox"
        payload = {
            "type": "Accept",
            "actor": accepter_id,
            "object": {"type": "Follow", "actor": actor_fqid, "object": accepter_id},
        }
        requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "User-Agent": "SocialDistribution/1.0"},
            timeout=10,
        )
    except Exception:
        pass


def approve_remote_follow(request, req_id):
    """Approves a follow request from a remote actor. Records RemoteFollower, notifies requester via Accept."""
    remote_req = get_object_or_404(RemoteFollowRequest, id=req_id, target_id=request.session.get('author_id'))
    name = remote_req.actor_display_name or "Remote author"
    actor_fqid = _normalize_fqid(remote_req.actor_fqid)
    target = remote_req.target
    remote_req.delete()
    # Record that this remote actor follows us (for friends = mutual follow logic)
    RemoteFollower.objects.update_or_create(
        actor_fqid=actor_fqid, target=target,
        defaults={"actor_display_name": name, "actor_url": actor_fqid},
    )
    # Notify requester so their Remote Following updates
    _send_accept_to_requester(request, actor_fqid=actor_fqid, accepter=target)
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
    # Remote followers: remote actors who follow us (approved)
    remote_followers_raw = list(
        RemoteFollower.objects.filter(target=author).order_by("created_at")
    )
    following_fqids = {_normalize_fqid(rf.followed_fqid) for rf in remote_followings}
    follower_by_fqid = {_normalize_fqid(r.actor_fqid): r for r in remote_followers_raw}
    follower_fqids = set(follower_by_fqid)
    # Remote friends: ONLY mutual (both follow each other) - appear ONLY here, not in other sections
    remote_friends = [
        {"fqid": norm_fqid, "display_name": follower_by_fqid[norm_fqid].actor_display_name or "Remote author"}
        for norm_fqid in follower_fqids
        if norm_fqid in following_fqids
    ]
    mutual_fqids = {rf["fqid"] for rf in remote_friends}
    # Remote following: only we follow them, they do NOT follow us (exclude mutual)
    remote_followings_display = []
    for rf in remote_followings:
        norm_fqid = _normalize_fqid(rf.followed_fqid)
        if norm_fqid not in mutual_fqids:
            remote_followings_display.append({"fqid": norm_fqid, "display_name": "Remote author"})
    # Remote followers: only they follow us, we do NOT follow them (exclude mutual)
    remote_followers = [
        r for r in remote_followers_raw
        if _normalize_fqid(r.actor_fqid) not in mutual_fqids
    ]

    return render(request, "connections.html", {
        "followers": followers,
        "followings": followings,
        "friends": friends,
        "remote_followings": remote_followings_display,
        "remote_followers": remote_followers,
        "remote_friends": remote_friends,
    })


def get_admin_hosted_image(request, image_id):
    """
    Serve hosted image by id for Markdown embedding.
    Uses AdminHostedImage model (ImageField).
    """
    hosted = get_object_or_404(AdminHostedImage, id=image_id)
    if not hosted.content or not hosted.content_type:
        return HttpResponse(status=404)
    try:
        binary_data = base64.b64decode(hosted.content)
    except (ValueError, TypeError):
        return HttpResponse(status=404)
    return HttpResponse(binary_data, content_type=hosted.content_type)


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
        try:
            base = request.build_absolute_uri("/")[:-1]
            author_base = (me.host or "").strip().rstrip("/") or base
            if "/api" not in author_base:
                author_base = f"{author_base.rstrip('/')}/api"
            if author_base.startswith("http://"):
                author_base = "https" + author_base[4:]
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
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "SocialDistribution/1.0 (+https://github.com/uofa-cmput404/w26-socialdistribution-project-burlywood)",
            }
            payload = {"type": "follow", "actor": actor_info, "object": object_info}
            logger.info("Sending follow to inbox url=%s actor=%s object=%s", inbox_url, actor_info.get("id"), normalized)
            resp = requests.post(
                inbox_url,
                json=payload,
                headers=headers,
                timeout=15,
                allow_redirects=False,
            )
            logger.info("Follow POST response status=%s url=%s body=%s", resp.status_code, inbox_url, resp.text[:200] if resp.text else "")
            if resp.status_code in (301, 302, 307, 308):
                loc = resp.headers.get("Location", "")
                if loc and loc != inbox_url:
                    resp = requests.post(loc, json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 202, 204):
                RemoteFollow.objects.create(follower=me, followed_fqid=normalized)
                messages.success(request, "Follow request sent!", extra_tags="follow")
            else:
                err_detail = resp.reason or ""
                try:
                    err_json = resp.json() if resp.text else {}
                    err_detail = err_json.get("error") or err_json.get("detail") or err_detail
                except (ValueError, AttributeError):
                    if resp.text and not resp.text.strip().startswith("<"):
                        err_detail = resp.text[:150]
                if not err_detail:
                    err_detail = resp.text[:100] if resp.text else "no details"
                messages.error(
                    request,
                    f"Inbox rejected ({resp.status_code}): {err_detail} — armdb may not have received the request.",
                )
                logger.warning("Follow inbox rejected status=%s body=%s", resp.status_code, resp.text[:300])
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not reach remote inbox: {str(e)[:100]}")
            logger.warning("Follow POST failed: %s", e)

    referer = request.META.get("HTTP_REFERER")
    if referer:
        try:
            base_url = request.build_absolute_uri('/')[:-1]
            match = resolve(referer.replace(base_url, ""))
            if match.url_name in ("ProfileDisplay", "RemoteProfileDisplay", "connections"):
                request.session["last_feed_url"] = referer
        except (Resolver404, ValueError):
            pass
    return redirect(request.session.get("last_feed_url", referer or "/"))


def unfollow_remote_author(request, fqid):
    """
    Unfollow a remote author (stop following them). Does NOT remove them from RemoteFollower.
    If they were a friend, they move to Remote Followers (they still follow you).
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
            base_url = request.build_absolute_uri('/')[:-1]
            match = resolve(referer.replace(base_url, ""))
            if match.url_name in ("ProfileDisplay", "RemoteProfileDisplay", "connections"):
                request.session["last_feed_url"] = referer
        except (Resolver404, ValueError):
            pass
    return redirect(request.session.get("last_feed_url", referer or "/"))


def remove_remote_follower(request, fqid):
    """
    Remove a remote follower (revoke their follow). Removes them from Remote Followers list.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    me = Author.objects.get(id=request.session["author_id"])
    normalized = _normalize_fqid(fqid)
    deleted, _ = RemoteFollower.objects.filter(actor_fqid=normalized, target=me).delete()
    if deleted:
        messages.success(request, "Remote follower removed.", extra_tags="follow")
    else:
        messages.info(request, "Follower was already removed.", extra_tags="follow")
    return redirect("connections")

def RemoteProfileDisplay(request, fqid):
    """
    Displays the profile of a remote author. Fetches author and entries from remote node.
    """
    logged_in_id = request.session.get("author_id")
    public_entries = []

    remote_author_url = fqid.rstrip("/").replace("http://", "https://")
    normalized_fqid = _normalize_fqid(remote_author_url)
    if not normalized_fqid or "/api/authors/" not in normalized_fqid:
        raise Http404("Invalid remote author URL")

    try:
        authorInfo = requests.get(
            remote_author_url,
            headers={"Accept": "application/json"},
            timeout=10,
            
        )
        authorInfo.raise_for_status()
        author = authorInfo.json()
    except requests.RequestException:
        return render(request, "error.html", {"message": "Could not load remote author profile."})

    match = re.search(r"/api/authors/([^/]+)/?$", remote_author_url)
    if not match:
        return render(request, "error.html", {"message": "Invalid remote author id."})

    author_id = match.group(1)
    base_host = remote_author_url.split("/api/authors/")[0]

    try:
        entryInfo = requests.get(
            f"{base_host}/api/authors/{author_id}/entries/",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        entryInfo.raise_for_status()
        entry_json = entryInfo.json()
    except requests.RequestException:
        entry_json = {}

    user_fqid = None
    if logged_in_id:
        base = request.build_absolute_uri('/')[:-1].replace("http://", "https://")
        user_fqid = f"{base}/api/authors/{logged_in_id}"
        

    raw_entries = []
    if isinstance(entry_json, list):
        raw_entries = entry_json
    else:
        raw_entries = (
            entry_json.get("src")
            or entry_json.get("entries")
            or entry_json.get("items")
            or []
        )

    for entry in raw_entries:
        if entry.get("visibility") != "PUBLIC":
            continue

        clean_id = (entry.get("id") or "").rstrip("/")
        if not clean_id:
            continue
        entry["clean_id"] = clean_id

        remote_comments = ((entry.get("comments") or {}).get("src")) or []
        
        # Fix bad remote comment author display names
        for c in remote_comments:
            if not isinstance(c, dict):
                continue

            auth = c.get("author")
            if not isinstance(auth, dict):
                continue

            cid = (auth.get("id") or "").rstrip("/")
            display = (auth.get("displayName") or "").strip()

            needs_fix = (
                not display
                or display.isdigit()
                or display.endswith("_author")
                or display == cid.split("/")[-1]
            )

            print("HEROKU COMMENT RAW:", c)
            print("HEROKU AUTHOR RAW:", auth)
            print("HEROKU CID:", cid)
            print("HEROKU DISPLAY BEFORE:", display)
            print("HEROKU NEEDS FIX:", needs_fix)

            if cid and needs_fix:
                match_author = re.search(r"/api/authors/([^/]+)/?$", cid)
                if not match_author:
                    continue

                author_key = match_author.group(1)
                fixed_name = None

                local_base = request.build_absolute_uri('/').rstrip('/').replace("http://", "https://")
                for c in remote_comments:
                    if not isinstance(c, dict):
                        continue

                    auth = c.get("author")
                    if not isinstance(auth, dict):
                        continue

                    cid = (auth.get("id") or "").rstrip("/")
                    display = (auth.get("displayName") or "").strip()

                    needs_fix = (
                        not display
                        or display.isdigit()
                        or display.endswith("_author")
                        or display == cid.split("/")[-1]
                    )

                    if not (cid and needs_fix):
                        continue

                    fixed_name = None

                    if cid.startswith(f"{local_base}/api/authors/"):
                        match_author = re.search(r"/api/authors/([^/]+)/?$", cid)
                        if match_author:
                            author_key = match_author.group(1)
                            if author_key.isdigit():
                                local_author = Author.objects.filter(id=int(author_key)).first()
                                if local_author:
                                    fixed_name = local_author.name or local_author.username

                    if not fixed_name:
                        try:
                            author_resp = requests.get(
                                cid,
                                headers={"Accept": "application/json"},
                                timeout=5,
                            )
                            if author_resp.status_code == 200:
                                author_data = author_resp.json()
                                fixed_name = (
                                    author_data.get("displayName")
                                    or author_data.get("name")
                                    or author_data.get("username")
                                )
                        except Exception as e:
                            print("REMOTE AUTHOR FETCH ERROR:", cid, str(e))

                    if fixed_name:
                        auth["displayName"] = fixed_name

        entry["fetched_comments"] = remote_comments
        entry["comment_count"] = len(remote_comments)

        remote_likes_src = (entry.get("likes") or {}).get("src", [])
        remote_like_count = (entry.get("likes") or {}).get("count", 0)

        remote_user_liked = False
        for like in remote_likes_src:
            like_author = (like.get("author") or {}).get("id")
            # Compare by author ID number only, as host varies
            if user_fqid == like_author:
                remote_user_liked = True
                break

        entry["liked_by_user"] = remote_user_liked

        entry["like_count"] = entry["likes"]["count"]
        public_entries.append(entry)

    is_following = False
    if logged_in_id and normalized_fqid:
        is_following = RemoteFollow.objects.filter(
            follower_id=logged_in_id, followed_fqid=normalized_fqid
        ).exists()

    request_sent = False

    context = {
        "author": author,
        "followers_count": 0,
        "following_count": 0,
        "is_following": is_following,
        "request_sent": request_sent,
        "logged_in_id": logged_in_id,
        "public_entries": public_entries,
        "author_fqid": normalized_fqid,
    }
    return render(request, "remoteprofileview.html", context)