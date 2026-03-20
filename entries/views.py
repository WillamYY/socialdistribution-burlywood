import base64
from email.mime import base
import markdown
import bleach
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, resolve, Resolver404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from .models import Entry
from core.models import Author
from core.services import maybe_sync_github_for_stream
from interactions.models import Like, Comment

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
                entry.content = render_safe_markdown(text_content)
            else:
                entry.content = text_content
            
            entry.contentType = contentType

    # Update universal fields
    entry.title = request.POST.get("title", entry.title)
    entry.description = request.POST.get("description", entry.description)
    entry.visibility = request.POST.get("visibility", entry.visibility)

    return True, None   # Success

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
            return render(request, "entries/create_entry.html", {"entry": new_entry})
        
        # If successful, commit it to the database
        new_entry.save()
        return redirect("view_my_entries")

    # Show the empty form for GET requests
    return render(request, "entries/create_entry.html")

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
            return render(request, "entries/edit_entry.html", {"entry": entry})
        
        # Commit the updates to the database
        entry.save()
        return redirect("view_my_entries")
    
    return render(request, "entries/edit_entry.html", {"entry": entry})

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

    return redirect("view_my_entries")

def stream_view(request):
    """
    Stream view: shows all entries the author should know about.
    US#25: Stream shows all entries I should know about.
    US#26: All public entries from the node (discoverability).
    US#27: Unlisted and friends-only entries from authors I follow.
    US#28: Most recent version (we fetch from DB - always current).
    US#29: Deleted entries excluded (hard-deleted, so not in DB).
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
    # US#27: UNLISTED from following; FRIENDS from friends only
    # US#29: No DELETED (hard-delete removes from DB)
    local_entries = list(
        Entry.objects.filter(
            Q(visibility="PUBLIC")
            | Q(author_id__in=following_ids, visibility="UNLISTED")
            | Q(author_id__in=friend_ids, visibility="FRIENDS")
        )
        .select_related("author")
        .order_by("-published")
    )

    # Public entries from IncomingNode (remote nodes we pull from)
    from core.remote import fetch_remote_public_entries
    remote_entries = fetch_remote_public_entries()

    # Combine and sort by published (newest first)
    def _sort_key(e):
        p = getattr(e, "published", None)
        if hasattr(p, "isoformat"):
            return p.isoformat()
        return str(p) if p else ""

    entries = sorted(
        local_entries + remote_entries,
        key=_sort_key,
        reverse=True,
    )

    # Build the current user's URL
    base_url = request.build_absolute_uri('/')[:-1]

    for entry in entries:
        if getattr(entry, "is_remote", False):
            continue
        entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        
        # Fetch the count of interactions
        entry.comment_count = Comment.objects.filter(entry=entry_url).count()
        entry.like_count = Like.objects.filter(object=entry_url).count()
        
        if "author_id" in request.session:
            user_fqid = f"{base_url}/api/authors/{request.session['author_id']}"
            entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
        
    return render(
        request,
        "entries/stream.html",
        {"entries": entries, "viewer": viewer},
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
            | Q(author_id__in=following_ids, visibility="UNLISTED")
            | Q(author_id__in=friend_ids, visibility="FRIENDS")
        )
        .select_related("author")
        .order_by("-published")
    )

    payload = []
    base = request.build_absolute_uri("/")[:-1]
    for entry in entries:
        entry_url = f"{base}/app/entry/{entry.id}/"
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
        entry.like_count = Like.objects.filter(object=entry_url).count()
        entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()

        # fetch comments
        entry.fetched_comments = Comment.objects.filter(entry=entry_url).order_by('published')

        # all objects liked by current user
        liked_objects = Like.objects.filter(author=user_fqid).values_list("object", flat=True)
        
        # extract UUIDs from liked objects
        liked_uuids = {
            obj.rstrip("/").split("/")[-1]
            for obj in liked_objects
        }

        for comment in entry.fetched_comments:
            # extract author id from URL
            author_id = comment.author.rstrip("/").split("/")[-1]

            try:
                author = Author.objects.get(id=author_id)
                comment.author_name = author.name
            except Author.DoesNotExist:
                comment.author_name = comment.author  # fallback

            comment_uuid = comment.id.rstrip("/").split("/")[-1]

            comment.like_count = Like.objects.filter(
                object__endswith=comment_uuid
            ).count()

            comment.liked_by_user = comment_uuid in liked_uuids

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
        entry.like_count = Like.objects.filter(object=entry_url).count()
        entry.fetched_comments = Comment.objects.filter(entry=entry_url).order_by('published')
        
        # Only check for "Unlike" state
        if user_fqid:
            entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
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

    # Base Entry Interactions
    entry.like_count = Like.objects.filter(object=entry_url).count()
    entry.fetched_comments = Comment.objects.filter(entry=entry_url).order_by('published')

    # Check if the logged-in user liked the this entry
    if logged_in_id:
        user_fqid = f"{base_url}/api/authors/{logged_in_id}"
        entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
    else:
        entry.liked_by_user = False

    # Fetch data for each comment
    for comment in entry.fetched_comments:
        # extract author id from FQID
        author_id = comment.author.rstrip("/").split("/")[-1]

        try:
            author = Author.objects.get(id=author_id)
            comment.author_name = author.username
        except Author.DoesNotExist:
            comment.author_name = comment.author

        comment_url = comment.id
        comment.like_count = Like.objects.filter(object=comment_url).count()

        if logged_in_id:
            user_fqid = f"{base_url}/api/authors/{logged_in_id}"
            comment.liked_by_user = Like.objects.filter(object=comment_url, author=user_fqid).exists()

    # Check the visibility for the logged-in user
    allowed = check_visibility(entry, logged_in_id)

    return render(request, "entries/entry.html", {
        "entry": entry,
        "allowed": allowed,
        "return_url": return_url,
    })