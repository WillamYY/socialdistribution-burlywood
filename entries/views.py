import base64
import re
import markdown
import bleach
import logging
from types import SimpleNamespace
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, resolve, Resolver404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from .models import Entry, RemoteEntry
from core.models import Author, AdminHostedImage, RemoteFollow, RemoteFollower, IncomingNode
from core.services import maybe_sync_github_for_stream
from core.remote import federate_entry_create_or_update, federate_entry_deleted, fetch_remote_public_entries
from interactions.models import Like, Comment
import requests
import json
from api.serializers import CommentSerializer
from django.utils import timezone


logger = logging.getLogger(__name__)


def _fqid_variants(url):
    """http/https and trailing-slash variants so Like lookups match how browsers / nodes store FQIDs."""
    if not url:
        return []
    u = str(url).strip().rstrip("/")
    out = {u, u + "/"}
    if u.startswith("http://"):
        out.add("https://" + u[len("http://") :])
    elif u.startswith("https://"):
        out.add("http://" + u[len("https://") :])
    return list(out)


def like_count_for_object(object_url):
    return Like.objects.filter(object__in=_fqid_variants(object_url)).count()


def entry_liked_by_user(object_url, user_fqid):
    if not user_fqid or not object_url:
        return False
    return Like.objects.filter(
        object__in=_fqid_variants(object_url),
        author__in=_fqid_variants(user_fqid),
    ).exists()


def _author_display_name_from_fqid(author_fqid):
    if not author_fqid:
        return "Unknown"
    s = author_fqid.rstrip("/")
    match = re.search(r"/authors?/(\d+)/?$", s)
    if match and match.group(1).isdigit():
        try:
            a = Author.objects.get(id=int(match.group(1)))
            return a.name or a.username
        except (Author.DoesNotExist, ValueError):
            pass
    return s.split("/")[-1] or "Unknown"


def _comment_host_from_id(comment_id):
    m = re.match(r"https?://([^/]+)", comment_id or "")
    return m.group(1) if m else ""


def comments_display_from_queryset(comments_qs, request, logged_in_id):
    """
    Build comment dicts for entry.html: always use local DB text so remote authors' comments
    still show even if IncomingNode lookup or GET to their node fails.
    """
    base_url = request.build_absolute_uri("/")[:-1]
    user_fqid = f"{base_url}/api/authors/{logged_in_id}" if logged_in_id else None
    my_host = request.get_host()
    out = []
    for c in comments_qs.order_by("published"):
        author_name = _author_display_name_from_fqid(c.author)
        comment_host = _comment_host_from_id(c.id)
        out.append(
            {
                "id": c.id,
                "comment": c.comment,
                "published": c.published,
                "author_name": author_name,
                "local": comment_host == my_host,
                "like_count": like_count_for_object(c.id),
                "liked_by_user": entry_liked_by_user(c.id, user_fqid),
            }
        )
    return out


def _finalize_remote_comment_for_template(comment_dict, request, logged_in_id, original_stub=None):
    """
    Normalize API/GET comment JSON (and fallbacks) to keys expected by remoteentry.html.
    original_stub: list item from entry['comments']['src'] when GET fails.
    """
    base_url = request.build_absolute_uri("/")[:-1]
    user_fqid = f"{base_url}/api/authors/{logged_in_id}" if logged_in_id else None
    my_host = request.get_host()

    d = dict(comment_dict) if comment_dict else {}
    stub = original_stub or {}
    if not d.get("id"):
        d["id"] = stub.get("id")
    if not d.get("comment"):
        d["comment"] = stub.get("comment") or ""
    if not d.get("published"):
        d["published"] = stub.get("published")

    cid = d.get("id") or stub.get("id")
    auth = d.get("author") if d.get("author") is not None else stub.get("author")
    if isinstance(auth, dict):
        d["author_name"] = auth.get("displayName") or _author_display_name_from_fqid(auth.get("id", ""))
    elif isinstance(auth, str):
        d["author_name"] = _author_display_name_from_fqid(auth)
    else:
        d["author_name"] = _author_display_name_from_fqid("")

    likes = d.get("likes")
    if isinstance(likes, dict) and "count" in likes:
        d["like_count"] = likes.get("count", 0)
    elif cid:
        d["like_count"] = like_count_for_object(cid)
    else:
        d["like_count"] = 0

    d["liked_by_user"] = entry_liked_by_user(cid, user_fqid) if cid else False
    d["local"] = _comment_host_from_id(cid) == my_host if cid else False
    return d


def _stored_remote_entry_to_stream_obj(remote_entry, viewer_fqid=None):
    """
    Helper function to adapt a stored RemoteEntry row into the stream object.
    Create a nested author object
    Mark the entry as remote
    Compute liked_by_user for the current viewer
    """
    # Normalize the object URL
    object_url = str(remote_entry.fqid).rstrip("/")
    viewer_fqid = (viewer_fqid or "").rstrip("/")

    # Check whether the current viewer liked this entry (FQID variants for http/https etc.)
    liked_by_user = entry_liked_by_user(object_url, viewer_fqid) if viewer_fqid else False
    
    # Fetch likes and comments objects
    likes_obj = remote_entry.raw_payload.get("likes") or {}
    comments_obj = remote_entry.raw_payload.get("comments") or {}

    # Return the object format for stream view
    return SimpleNamespace(
        id=remote_entry.fqid,
        title=remote_entry.title or "",
        description=remote_entry.description or "",
        content=remote_entry.content or "",
        content_raw=remote_entry.content_raw,
        contentType=remote_entry.contentType or "text/plain",
        visibility=remote_entry.visibility,
        published=remote_entry.published,
        author=SimpleNamespace(
            id=remote_entry.author_fqid,
            username=remote_entry.author_display_name or "Remote",
            github=remote_entry.author_github or "",
            profile_image=remote_entry.author_profile_image or "",
            host=remote_entry.author_host or "",
        ),
        is_remote=True,
        remote_web=(remote_entry.web or remote_entry.fqid),
        like_count = likes_obj.get("count", 0) if isinstance(likes_obj, dict) else 0,
        comment_count = comments_obj.get("count", 0) if isinstance(comments_obj, dict) else 0,
        liked_by_user=liked_by_user,
        stored_remote=True,
    )

def _normalize_url_for_match(url):
    if not url:
        return ""
    url = str(url).strip().rstrip("/")
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


def _comment_matches_entry(comment_entry_url, canonical_entry_fqid):
    left = _normalize_url_for_match(comment_entry_url)
    right = _normalize_url_for_match(canonical_entry_fqid)

    if not left or not right:
        return False

    if left == right:
        return True

    return left.split("/")[-1] == right.split("/")[-1]

def _serialize_local_comment_for_page(comment, request=None):
    """
    Safe fallback serializer for local comments when remote/detail lookup fails.
    """
    author_name = "Unknown"
    author_url = str(comment.author).rstrip("/")

    try:
        local_base = ""
        if request:
            local_base = request.build_absolute_uri("/").rstrip("/").replace("http://", "https://")

        match = re.search(r"/authors/(\d+)/?$", author_url)

        if match and local_base and author_url.startswith(f"{local_base}/api/authors/"):
            author_obj = Author.objects.filter(id=int(match.group(1))).first()
            if author_obj:
                author_name = author_obj.username
            else:
                author_name = author_url.split("/")[-1]
        else:
            author_name = author_url.split("/")[-1]

            try:
                author_host_match = re.search(r"^https?://[^/]+", author_url)
                author_host = author_host_match.group(0) if author_host_match else None

                if author_host:
                    node = IncomingNode.objects.filter(url=author_host + "/").first()
                    if node:
                        resp = requests.get(
                            author_url,
                            auth=(node.username, node.password),
                            timeout=5,
                        )
                        if resp.status_code < 400:
                            author_json = json.loads(resp.text)
                            author_name = (
                                author_json.get("displayName")
                                or author_json.get("username")
                                or author_name
                            )
            except Exception:
                pass

    except Exception:
        author_name = author_url.split("/")[-1]

    comment_id = str(comment.id).rstrip("/")
    comment_tail = comment_id.split("/")[-1]

    like_qs = (
        Like.objects.filter(object=comment_id)
        | Like.objects.filter(object=comment_id + "/")
        | Like.objects.filter(object__endswith="/" + comment_tail)
    ).distinct()

    return {
        "type": "comment",
        "id": comment_id,
        "author": {
            "id": author_url,
            "displayName": author_name,
        },
        "author_name": author_name,
        "comment": comment.comment,
        "contentType": comment.contentType,
        "published": comment.published,
        "local": True,
        "like_count": like_qs.count(),
        "liked_by_user": False,
    }

def check_visibility(entry, viewer_id, is_list=False):
    """
    Helper function to verify if a user can see an entry.
    """
    # Not found if entry is DELETED
    if entry.visibility == "DELETED":
        return False
    # Anyone with the link can see Public and Unlisted
    if entry.visibility == "PUBLIC":
        return True
    if entry.visibility == "UNLISTED":
        if not is_list:
            # Direct link access
            return True
        else:
            # If from list, only the author or a follower can see it in a feed
            if not viewer_id:
                return False
            if str(entry.author.id) == str(viewer_id):
                return True
            if entry.author.followers.filter(id=viewer_id).exists():
                return True
            return False

    # If not logged in, cannot see anything else
    if not viewer_id:
        return False
        
    # Author can always see their own non-deleted stuff
    if str(entry.author.id) == str(viewer_id):
        return True
        
    # Friends check for mutual followers
    if entry.visibility == "FRIENDS":
        try:
            viewer = Author.objects.get(id=viewer_id)
            entry_author = Author.objects.get(id=entry.author.id)
            # Check if the viewer is in entry author's friends list
            return viewer in entry_author.friends()
        except Author.DoesNotExist:
            return False
            
    return False

def validate_markdown_image_syntax(text_content):
    """
    Helper function to detect broken Markdown image syntax.

    Return:
    None if no error, else an error string message.
    """
    # Check if user probably wants to use Markdown image syntax
    if not text_content or "![" not in text_content:
        return None
        
    # If image marker ![ exists, but no proper ( after it
    if re.search(r'!\[[^\]]*\](?!\()', text_content):
        return (
            "Invalid Markdown image syntax. Use the format: ![alt text](url)"
        )

    # If not enclose the URL with )
    if re.search(r'!\[[^\]]*\]\([^)]*$', text_content):
        return (
            "Markdown image link is not enclosed with ')'. Use the format: ![alt text](url)"
        )

    # If no image URL in ()
    if re.search(r'!\[[^\]]*\]\(\s*\)', text_content):
        return (
            "Markdown image URL cannot be empty. Use the format: ![alt text](url)"
        )

    # Otherwise valid syntax
    return None 

def render_safe_markdown(text_content):
    """
    Helper function to convert raw Markdown text to HTML and sanitize it to prevent XSS.
    """
    if not text_content:
        return ""

    # Convert Markdown to HTML
    html_raw = markdown.markdown(text_content, extensions=["extra", "codehilite"])
    
    # Define safe tags and attributes
    allowed_tags = [
        "p", "br",
        "strong", "em", "b", "i",
        "ul", "ol", "li",
        "blockquote",
        "code", "pre", "hr",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "a", "img",
        "table", "thead", "tbody", "tr", "th", "td"
    ]

    allowed_attributes = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title"],
    }

    # Sanitize and return the safe HTML
    return bleach.clean(html_raw, tags=allowed_tags, attributes=allowed_attributes)

def update_entry_from_request(request, entry):
    """
    Helper function to process form data, validate it, and update an Entry object.
    Returns: (is_success: bool, error_message: str or None)
    """
    contentType = request.POST.get("contentType", "")
    text_content = request.POST.get("content", "")
    image = request.FILES.get("image_file")

    # Check if an image entry or text entry being created/edited
    if image:
        # Check the actual file type
        if not image.content_type.startswith("image/"):
            return False, "Only an image in .jpg/.png format is allowed."
        
        # Overwrite the data with the new image
        entry.contentType = f"{image.content_type};base64"
        entry.content = base64.b64encode(image.read()).decode("utf-8")
        # No "raw" text for images
        entry.content_raw = None
    else:
        # Check if text content is provided for text entries
        if "text" in contentType:
            if not text_content.strip():
                return False, "Text content is required for a text entry."
            
            # Store the raw text
            entry.content_raw = text_content

            # Check for text type
            if contentType == "text/markdown":
                markdown_error = validate_markdown_image_syntax(text_content)
                if markdown_error:
                    return False, markdown_error
                entry.content = render_safe_markdown(text_content)
            else:
                entry.content = text_content
            
            entry.contentType = contentType

    # Update universal fields
    entry.title = request.POST.get("title", entry.title)
    entry.description = request.POST.get("description", entry.description)
    entry.visibility = request.POST.get("visibility", entry.visibility)

    return True, None   # Success

def get_admin_hosted_images(request):
    """
    Get node-admin hosted images with the absolute URL.
    """
    images = []
    for image in AdminHostedImage.objects.order_by("-uploaded_at"):
        if not image.content or not image.content_type:
            continue

        absolute_url = request.build_absolute_uri(
            reverse("admin_hosted_image_file", kwargs={"image_id": image.id})
        )
        safe_title = (image.title or "").replace("]", "")
        images.append({
            "title": image.title,
            "absolute_url": absolute_url,
            "markdown": f"![{safe_title}]({absolute_url})",
        })
    return images

def create_entry(request):
    """
    Handles the creation of a new entry, including processing image uploads and text content.
    """
    if request.method == "POST":
        if not request.session.get("author_id"):
            return redirect("/app/login")

        # Get the author first
        author = Author.objects.get(id=request.session["author_id"])
        
        # Create a blank Entry instance in memory
        new_entry = Entry(author=author)
        
        # Process the form data
        success, error_msg = update_entry_from_request(request, new_entry)
        
        if not success:
            messages.error(request, error_msg)
            # Pass new_entry back to continue
            return render(request, "entries/create_entry.html", {"entry": new_entry, "admin_hosted_images": get_admin_hosted_images(request)})
        
        # If successful, commit it to the database
        new_entry.save()
        federate_entry_create_or_update(new_entry, request)
        return redirect("view_my_entries")

    # Show the empty form for GET requests
    return render(request, "entries/create_entry.html", {"admin_hosted_images": get_admin_hosted_images(request)})

def edit_entry(request, entry_id):
    """
    Handles the editing of an existing entry. 
    Only the author of the entry can edit it.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])
    entry = get_object_or_404(Entry, id=entry_id, author=author)

    if request.method == "POST":
        
        # Process the form data
        success, error_msg = update_entry_from_request(request, entry)
        
        if not success:
            messages.error(request, error_msg)
            return render(request, "entries/edit_entry.html", {"entry": entry, "admin_hosted_images": get_admin_hosted_images(request)})
        
        # Commit the updates to the database
        # `published` is used for "most recent first" ordering, so treat edits as
        # a new "publish" time even though the Entry model uses `auto_now_add`.
        entry.published = timezone.now()
        entry.save()
        federate_entry_create_or_update(entry, request)
        return redirect("view_my_entries")
    
    return render(request, "entries/edit_entry.html", {"entry": entry, "admin_hosted_images": get_admin_hosted_images(request)})

@require_POST
def delete_entry(request, entry_id):
    """
    Handles the soft deletion of an entry. 
    Only the author of the entry can delete it.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])
    
    # Fetch the entry by this author
    entry = get_object_or_404(Entry, id=entry_id, author=author)
    
    # Soft delete by changing visibility to DELETED
    entry.visibility = "DELETED"
    entry.save()
    federate_entry_deleted(entry, request)

    return redirect("view_my_entries")

def stream_view(request):
    """
    Stream view: shows all entries the author should know about.
    US#25: Stream shows all entries I should know about.
    US#26: All public entries from the node (discoverability).
    US#27: Unlisted and friends-only entries from authors I follow.
    US#28: Most recent version (we fetch from DB - always current).
    US#29: Deleted entries excluded.
    US#31: Sorted with most recent entries first.
    GitHub activity is auto-synced when stream is viewed (throttled).
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    # Auto-sync GitHub activity so new pushes/events show up without user action (User Story #5)
    maybe_sync_github_for_stream()

    viewer = get_object_or_404(Author, id=request.session["author_id"])

    # Authors I follow
    following_ids = list(viewer.following.values_list("id", flat=True))
    # Friends = mutual follow
    friend_ids = list(viewer.friends().values_list("id", flat=True))

    # US#26: All PUBLIC entries from any author on the node
    # US#27: UNLISTED from following (and viewer's own); FRIENDS from friends (and viewer's own)
    # US#29: No DELETED (hard-delete removes from DB)
    local_entries = list(
        Entry.objects.filter(
            Q(visibility="PUBLIC")
            | Q(author_id=viewer.id, visibility__in=["UNLISTED", "FRIENDS"])  # author sees own unlisted/friends
            | Q(author_id__in=following_ids, visibility="UNLISTED")
            | Q(author_id__in=friend_ids, visibility="FRIENDS")
        )
        .select_related("author")
        .order_by("-published")
    )
    
    # Relations for fetching remote entries directly from other nodes
    # Public entries from IncomingNode; UNLISTED from following; FRIENDS from remote friends (mutual follow)
    def _normalize_fqid_local(s):
        if not s:
            return ""
        s = str(s).strip().rstrip("/")
        if s.startswith("http://"):
            s = "https" + s[4:]
        return s
    following_remote_fqids = [
        _normalize_fqid_local(f)
        for f in RemoteFollow.objects.filter(follower=viewer).values_list("followed_fqid", flat=True)
    ]
    followers_remote_fqids = {
        _normalize_fqid_local(f)
        for f in RemoteFollower.objects.filter(target=viewer).values_list("actor_fqid", flat=True)
    }
    friends_remote_fqids = [f for f in following_remote_fqids if f in followers_remote_fqids]
    
    base_url_for_fetch = request.build_absolute_uri("/")[:-1]
    viewer_fqid = f"{base_url_for_fetch}/api/authors/{viewer.id}"

    # Filter the stored inbox entries
    stored_remote_entries_qs = (
        RemoteEntry.objects.filter(recipient=viewer).exclude(visibility="DELETED")
    )

    # Check current relationship before showing stored remote inbox entries in stream
    stored_remote_entries = []
    following_remote_set = set(following_remote_fqids)
    friends_remote_set = set(friends_remote_fqids)

    for remote_entry in stored_remote_entries_qs:
        remote_author_fqid = _normalize_fqid_local(remote_entry.author_fqid)
        visibility = remote_entry.visibility

        if visibility == "PUBLIC":
            pass

        elif visibility == "UNLISTED":
            if remote_author_fqid not in following_remote_set:
                continue

        elif visibility == "FRIENDS":
            if remote_author_fqid not in friends_remote_set:
                continue

        else:
            # Like DELETED
            continue

        stored_remote_entries.append(
            _stored_remote_entry_to_stream_obj(remote_entry, viewer_fqid=viewer_fqid)
        )
    
    
    # Truly live-fetched remote entries
    remote_entries = fetch_remote_public_entries(
        following_remote_fqids=following_remote_fqids,
        friends_remote_fqids=friends_remote_fqids,
        requested_by_fqid=viewer_fqid,
    )
    
    
    # Combine and sort by published (newest first)
    def _sort_key(entry):
        published = getattr(entry, "published", None)
        if hasattr(published, "isoformat"):
            return published.isoformat()
        return str(published) if published else ""
    
    # Keep both stored remote entries and live-fetched entries for temporary transition
    # Prefer the former over the latter
    combined_entries = local_entries + stored_remote_entries + remote_entries
    
    live_remote_duped = 0
    seen_remote_ids = set()
    deduped_entries = []
    # Remove duplicated remote entries from two sources
    for entry in combined_entries:
        if getattr(entry, "is_remote", False):
            # Remote entry checks
            remote_id = str(getattr(entry, "id", "")).rstrip("/")
            if remote_id in seen_remote_ids:
                live_remote_duped += 1
                continue
            seen_remote_ids.add(remote_id)
        deduped_entries.append(entry)
        
    """
    logger.info(
        "STREAM VIEW viewer=%s local=%s stored_remote=%s live_remote=%s deduped_live_remote=%s final=%s",
        viewer.id,
        len(local_entries),
        len(stored_remote_entries),
        len(remote_entries),
        live_remote_duped,
        len(deduped_entries),
    )
    """

    entries = sorted(
        deduped_entries,
        key=_sort_key,
        reverse=True,
    )

    # Build the current user's URL
    base_url = request.build_absolute_uri('/')[:-1]

    # Add interaction data for local entries
    for entry in entries:
        if getattr(entry, "is_remote", False):
            # Keep adapter flow for remote entries
            """
            if "author_id" in request.session:
                partial_fqid = f"{request.get_host()}/api/authors/{request.session['author_id']}"
                entry.liked_by_user = Like.objects.filter(object__endswith= re.search("/entries/([^/]+)",entry.id).group(1), author__endswith = partial_fqid).exists()
            """
            # Handles turning content into markdown
            if "markdown" in entry.contentType:
                entry.markdown = render_safe_markdown(entry.content)
            # Handles an image being stored in wrong way
            if hasattr(entry,"image"):
                entry.contentType = "image"
                entry.content = getattr(entry,"image")
            continue

        # If local, check local interactoins
        entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        
        # Fetch the count of interactions
        entry.comment_count = Comment.objects.filter(entry__endswith=entry.id).count()
        entry.like_count = like_count_for_object(entry_url)
        user_fqid = f"{base_url}/api/authors/{viewer.id}"
        entry.liked_by_user = entry_liked_by_user(entry_url, user_fqid)

    entries_local = [e for e in entries if not getattr(e, "is_remote", False)]
    entries_remote = [e for e in entries if getattr(e, "is_remote", False)]

    return render(
        request,
        "entries/stream.html",
        {
            "entries": entries,
            "entries_local": entries_local,
            "entries_remote": entries_remote,
            "viewer": viewer,
        },
    )



def stream_api(request, author_id):
    """
    Local API endpoint for the stream.
    Returns entries the author should see:
    - all PUBLIC entries on the node
    - UNLISTED entries from followed authors
    - FRIENDS entries from mutual friends
    """
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    session_author_id = request.session.get("author_id")
    if not session_author_id:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    if session_author_id != author_id:
        return JsonResponse({"detail": "Forbidden."}, status=403)

    viewer = get_object_or_404(Author, id=author_id)

    following_ids = list(viewer.following.values_list("id", flat=True))
    friend_ids = list(viewer.friends().values_list("id", flat=True))

    entries = (
        Entry.objects.filter(
            Q(visibility="PUBLIC")
            | Q(author_id=viewer.id, visibility__in=["UNLISTED", "FRIENDS"])
            | Q(author_id__in=following_ids, visibility="UNLISTED")
            | Q(author_id__in=friend_ids, visibility="FRIENDS")
        )
        .select_related("author")
        .order_by("-published")
    )

    payload = []
    base = request.build_absolute_uri("/")[:-1]
    for entry in entries:
        entry_url = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
        like_count = Like.objects.filter(object=entry_url).count()
        # optionally we could provide commentCount or the comments
        # themselves; the frontend currently doesn't need them.

        payload.append(
            {
                "type": "entry",
                "id": str(entry.id),
                "title": entry.title,
                "description": entry.description,
                "contentType": entry.contentType,
                "content": entry.content,
                "author": {
                    "type": "author",
                    "id": entry.author.id,
                    "displayName": entry.author.name or entry.author.username,
                    "username": entry.author.username,
                },
                "published": entry.published.isoformat(),
                "visibility": entry.visibility,
                "likeCount": like_count,
            }
        )

    return JsonResponse(
        {
            "type": "entries",
            "page_number": 1,
            "size": len(payload),
            "count": len(payload),
            "src": payload,
        }
    )


def view_my_entries(request):
    """
    Displays a list of entries created by the currently logged-in author, 
    ordered by publication date (newest first).
    GitHub activity is auto-synced when this page is viewed (same 10s throttle as stream).
    """
    if not request.session.get("author_id"): 
        return redirect("/app/login")

    maybe_sync_github_for_stream()

    author = Author.objects.get(id=request.session["author_id"])

    # Get all entries by this author, ordered by newest first
    entries = Entry.objects.filter(author=author).exclude(visibility="DELETED").order_by("-published")
    user_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author.id}"

    # Manually attach Like/Comment data for interactions
    for entry in entries:
        base = request.build_absolute_uri('/')[:-1]
        entry_url = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
        
        # entry likes
        entry.like_count = like_count_for_object(entry_url)
        entry.liked_by_user = entry_liked_by_user(entry_url, user_fqid)

        # fetch comments
        entry.fetched_comments = Comment.objects.filter(entry__endswith=entry.id).order_by('published')

        for comment in entry.fetched_comments:
            # Extract commenter id from author URL (commenter = who wrote comment, NOT entry.author)
            match = re.search(r'/authors?/(\d+)/?$', comment.author)
            commenter_id = match.group(1) if match else comment.author.rstrip("/").split("/")[-1]

            try:
                commenter = Author.objects.get(id=commenter_id)
                comment.author_name = commenter.name or commenter.username
            except (Author.DoesNotExist, ValueError):
                comment.author_name = comment.author

            comment.like_count = like_count_for_object(comment.id)
            comment.liked_by_user = entry_liked_by_user(comment.id, user_fqid)

    return render(request, "entries/my_entries.html", {"entries": entries})

def view_entries(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    logged_in_id = request.session.get('author_id')
    is_owner = logged_in_id == author.id

    entries = (Entry.objects.filter(author=author).exclude(visibility="DELETED").order_by("-published"))

    if not is_owner:
        if logged_in_id:
            viewer = get_object_or_404(Author, id=logged_in_id)
            if viewer in author.friends():
                # friend: show PUBLIC + FRIENDS + UNLISTED
                entries = entries.filter(visibility__in=['PUBLIC', 'FRIENDS', "UNLISTED"])
            elif viewer in author.followers.all():
                # follower: show PUBLIC + UNLISTED
                entries = entries.filter(visibility__in=["PUBLIC", "UNLISTED"])
            else:
                # non-friend: show only PUBLIC
                entries = entries.filter(visibility='PUBLIC')
        else:
            # not logged in: show only PUBLIC
            entries = entries.filter(visibility='PUBLIC')
        
    entries_list = list(entries)
    base = request.build_absolute_uri('/')[:-1]

    user_fqid = None
    if logged_in_id:
        user_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{logged_in_id}"

    # Manually attach Like/Comment data for the interactions
    for entry in entries_list:
        entry_url = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
        entry.like_count = like_count_for_object(entry_url)
        entry.fetched_comments = Comment.objects.filter(entry__endswith=entry.id).order_by("-published")
        
        # Only check for "Unlike" state
        if user_fqid:
            entry.liked_by_user = entry_liked_by_user(entry_url, user_fqid)
        else:
            entry.liked_by_user = False

    # owner sees all entries, including UNLISTED
    return render(request, 'entries/view_entries.html', {
        'author': author,
        'entries': entries_list,
    })

def get_entry(request, entry_id):
    """
    Get a single entry by ID
    Check visibility as well as Like/Comment data.
    """
    entry = get_object_or_404(Entry, id=entry_id)
    
    # Not found if entry is DELETED
    if entry.visibility == "DELETED":
        return HttpResponse(status=404)
    
    base_url = request.build_absolute_uri('/')[:-1]
    entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
    logged_in_id = request.session.get("author_id")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        try:
            # Resolve the URL to see which view function it points to
            match = resolve(referer.replace(base_url, ""))
            
            # Update the return URL only if came from a LIST view (i.e. stream, my-entries, etc.)
            list_views = ['stream', 'view_my_entries', 'view_entries', "ProfileDisplay"]
            
            if match.url_name in list_views:
                request.session['last_feed_url'] = referer
        except (Resolver404, ValueError):
            # If the URL doesn't match, don't update the session
            pass

    # Default to Stream if don't have a saved feed yet
    return_url = request.session.get('last_feed_url', reverse('stream'))

    canonical_entry_fqid = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}".rstrip("/")

    entry.like_count = Like.objects.filter(object=entry_url).count()

    all_known_comments = Comment.objects.all().order_by("published")
    entry_comments = [
        c for c in all_known_comments
        if _comment_matches_entry(c.entry, canonical_entry_fqid)
    ]

    if logged_in_id:
        user_fqid = f"{base_url}/api/authors/{logged_in_id}"
        entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
    else:
        user_fqid = None
        entry.liked_by_user = False

    comments = []

    for stored_comment in entry_comments:
        comment_id = str(stored_comment.id).rstrip("/")

        # Default fallback: always keep something displayable
        fallback_comment = _serialize_local_comment_for_page(stored_comment, request=request)

        if user_fqid:
            fallback_comment["liked_by_user"] = (
                Like.objects.filter(author=user_fqid, object=comment_id).exists()
                or Like.objects.filter(
                    author=user_fqid,
                    object__endswith=comment_id.split("/")[-1]
                ).exists()
            )

        # If comment is local, do not re-fetch it from API just to render it
        try:
            comment_host_match = re.search(r"^https?://([^/]+)", comment_id)
            comment_host = comment_host_match.group(1) if comment_host_match else None
        except Exception:
            comment_host = None

        if comment_host == request.get_host():
            comments.append(fallback_comment)
            continue

        # Remote comment: try to refresh from remote detail endpoint, but keep fallback on failure
        try:
            comment_full_host_match = re.search(r"^https?://[^/]+", comment_id)
            if not comment_full_host_match:
                comments.append(fallback_comment)
                continue

            comment_full_host = comment_full_host_match.group(0)
            comment_node = IncomingNode.objects.filter(url=comment_full_host + "/").first()

            if not comment_node:
                comments.append(fallback_comment)
                continue

            comment_info = requests.get(
                comment_id,
                auth=(comment_node.username, comment_node.password),
                timeout=8,
            )

            if comment_info.status_code >= 400:
                comments.append(fallback_comment)
                continue

            comment_json = json.loads(comment_info.text)
            comment_json["local"] = False
            comment_json["like_count"] = ((comment_json.get("likes") or {}).get("count", 0))

            author_obj = comment_json.get("author") or {}
            comment_json["author_name"] = (
                author_obj.get("displayName")
                or author_obj.get("username")
                or fallback_comment["author_name"]
            )

            if user_fqid:
                comment_json["liked_by_user"] = (
                    Like.objects.filter(author=user_fqid, object=comment_id).exists()
                    or Like.objects.filter(
                        author=user_fqid,
                        object__endswith=comment_id.split("/")[-1]
                    ).exists()
                )
            else:
                comment_json["liked_by_user"] = False

            comments.append(comment_json)

        except Exception:
            comments.append(fallback_comment)

    entry.fetched_comments = comments

    # Check the visibility for the logged-in user
    allowed = check_visibility(entry, logged_in_id)

    image_api_url = None
    if ";base64" in entry.contentType and "image" in entry.contentType:
        image_api_url = reverse("api:ApiEntryImage", kwargs={
            "author_id": entry.author.id,
            "entry_id": entry.id,
        })

    return render(request, "entries/entry.html", {
        "entry": entry,
        "allowed": allowed,
        "return_url": return_url,
        "image_api_url": image_api_url,
    })
"""
Handles displaying the page for remote entries
"""
def get_remote_entry(request,fqid):
    # Handles hardcoded solutions variables
    fuschia = False
    if re.match("https?://[^/]*fuchsia[^/]*",fqid):
        fuschia = True
    # Queries to find the correct fqid (Handles being sent distorted fqid)
    fqid = re.search("https?://[^/]+/api/authors/[^/]+/entries/[^/]+",fqid).group(0)
    fqid = fqid.rstrip("/").replace("http://", "https://")
    if "/api/" not in fqid:
        return HttpResponse(status=404)
    # Gets where the host ends
    index = fqid.index("/api/")
    logged_in_id = request.session.get("author_id")
    author_fqid = request.scheme + "://" + request.get_host() + "/api/authors/" + str(logged_in_id)
    # FORCES https for consistency
    fqid = fqid.rstrip("/").replace("http://", "https://")
    # Gets the entry
    node_credentials = get_object_or_404(IncomingNode, url=fqid[:index] + "/")
    entryInfo = requests.get(fqid.rstrip("/"), auth=(node_credentials.username, node_credentials.password))
    entryInfo.raise_for_status()
    entry = json.loads(entryInfo.text)
    """
    # Creates the list of allowed things to view
    allowed_visibility = ["PUBLIC","UNLISTED","FRIENDS"]
    if RemoteFollow.objects.filter(follower = logged_in_id,followed_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1]).exists():
        is_following = RemoteFollow.objects.get(follower = logged_in_id,followed_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1])
        remote_host = is_following.followed_fqid[:is_following.followed_fqid.index("/api")] + "/"
        credentials = IncomingNode.objects.get(url = remote_host)
        response = requests.get(
            f"{is_following.followed_fqid}/followers/{author_fqid}",
            headers={"Accept": "application/json"},
            auth=(credentials.username, credentials.password),
            timeout=10
        )
        if response.status_code < 400:
            if RemoteFollower.objects.filter(actor_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1],target = logged_in_id).exists():
                allowed_visibility.append("FRIENDS")
    """
    allowed = True
    comments = []
    """
    # HARDCODE SOLUTION FOR fuschia
    if fuschia:
        entry["comments"] = {}
        entry["comments"]["src"] = entry.get("commentsSrc", {})
    """
    entry_comments = entry.get("comments", {}).get("src") or []

    def _incoming_node_for_comment_host(host_base_raw):
        h = (host_base_raw or "").rstrip("/")
        if not h:
            return None
        for candidate in (h + "/", h):
            n = IncomingNode.objects.filter(url=candidate).first()
            if n:
                return n
        return None

    for stub in entry_comments:
        if not isinstance(stub, dict):
            continue
        comment_id = stub.get("id")
        if not comment_id:
            continue
        merged = None
        mhost = re.search(r"https?://([^/]+)", comment_id)
        comment_part_host = mhost.group(1) if mhost else ""

        if comment_part_host == request.get_host():
            try:
                suf = re.search(r"/commented/([^/]+)", comment_id)
                if suf:
                    cobj = Comment.objects.filter(id__endswith=f"/commented/{suf.group(1)}").first()
                    if cobj:
                        merged = CommentSerializer(cobj, context={"request": request}).data
            except Exception:
                merged = None
        else:
            try:
                full_m = re.search(r"https?://[^/]+", comment_id)
                if full_m:
                    comment_node = _incoming_node_for_comment_host(full_m.group(0))
                    if comment_node:
                        resp = requests.get(
                            comment_id.rstrip("/"),
                            auth=(comment_node.username, comment_node.password),
                            timeout=10,
                        )
                        if resp.status_code < 400:
                            merged = json.loads(resp.text)
            except Exception:
                merged = None

        comments.append(
            _finalize_remote_comment_for_template(
                merged or {},
                request,
                logged_in_id,
                original_stub=stub,
            )
        )

    entry["comments"]["src"] = comments
    # Image api url
    image_api_url = None
    if ";base64" in entry.get("contentType") and "image" in entry.get("contentType"):
        image_api_url = fqid[:index] + "/api/entries/" + fqid + "/image"
        image_api_url = reverse("api:ApiEntryImageGlobal", kwargs={"entry_fqid": fqid})
    # Handles Markdown
    if "markdown" in entry.get("contentType"):
        entry["markdown"] = render_safe_markdown(entry.get("content"))
    # Handles an image being stored in wrong way
    if hasattr(entry,"image"):
        entry.contentType = "image"
        entry.content = getattr(entry,"image")
    # Handles getting likes
    likes_obj = entry.get("likes") or {}
    entry["like_count"] = likes_obj.get("count", 0)
    base_url = request.build_absolute_uri("/")[:-1]
    entry_fqid_for_like = (entry.get("id") or fqid).strip().rstrip("/")
    user_fqid_remote = f"{base_url}/api/authors/{logged_in_id}" if logged_in_id else None
    entry["liked_by_user"] = (
        entry_liked_by_user(entry_fqid_for_like, user_fqid_remote) if user_fqid_remote else False
    )
    entry["fetched_comments"] = comments

    return_url = request.session.get('last_feed_url', reverse('stream'))
    return render(request, "entries/remoteentry.html", {
        "entry": entry,
        "allowed": allowed,
        "return_url": return_url,
        "image_api_url": image_api_url,
    })