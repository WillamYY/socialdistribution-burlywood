import base64
import markdown
import bleach
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from .models import Entry
from core.models import Author
from interactions.models import Like, Comment

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
        return redirect("my_entries")

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
        return redirect("my_entries")
    
    return render(request, "entries/edit_entry.html", {"entry": entry})

@require_POST
def delete_entry(request, entry_id):
    """
    Handles the deletion of an entry. 
    Only the author of the entry can delete it.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    author = Author.objects.get(id=request.session["author_id"])
    
    # Fetch the entry by this author
    entry = get_object_or_404(Entry, id=entry_id, author=author)
    
    # Remove it from the database
    entry.delete()
    
    return redirect("my_entries")

def get_entry_image(request, author_id, entry_id):
    """
    Returns the raw image data for an entry.
    Allows Markdown to link to images.
    """
    # Get the entry
    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    # Check if base64 data, implying an image
    if ";base64" not in entry.contentType:
        return HttpResponse("This entry is not an image.", status=404)

    # Extract the actual base64 string and the MIME type
    # MIME == Multipurpose Internet Mail Extension: type of data being transmitted over internet 
    mime_type = entry.contentType.split(';')[0]     # i.e. format like "image/png;base64"

    try:
        # Strip the content string to get the actual base64 data 
        content_str = entry.content
        if "," in content_str:  # i.e. data:image/png;base64,... prefix
            content_str = content_str.split(",")[1]
            
        image_binary = base64.b64decode(content_str.strip())
        # Return raw binary data with the correct MIME type
        return HttpResponse(image_binary, content_type=mime_type)
    except Exception as e:
        # Failed to decode base64; internal server error
        return HttpResponse(f"Failed to decode image: {str(e)}", status=500)

def stream_view(request):
    """
    Stream view: shows all entries the author should know about.
    US#25: Stream shows all entries I should know about.
    US#26: All public entries from the node (discoverability).
    US#27: Unlisted and friends-only entries from authors I follow.
    US#28: Most recent version (we fetch from DB - always current).
    US#29: Deleted entries excluded (hard-deleted, so not in DB).
    US#31: Sorted with most recent entries first.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    viewer = get_object_or_404(Author, id=request.session["author_id"])

    # Authors I follow
    following_ids = list(viewer.following.values_list("id", flat=True))
    # Friends = mutual follow
    friend_ids = list(viewer.friends().values_list("id", flat=True))

    # US#26: All PUBLIC entries from any author on the node
    # US#27: UNLISTED from following; FRIENDS from friends only
    # US#29: No DELETED (hard-delete removes from DB)
    entries = (
        Entry.objects.filter(
            Q(visibility="PUBLIC")
            | Q(author_id__in=following_ids, visibility="UNLISTED")
            | Q(author_id__in=friend_ids, visibility="FRIENDS")
        )
        .select_related("author")
        .order_by("-published")
    )

    # Build the current user's URL
    user_fqid = f"{request.build_absolute_uri('/')[:-1]}/authors/{viewer.id}"

    for entry in entries:
        entry_url = f"{request.build_absolute_uri('/')[:-1]}/app/entry/{entry.id}/"

        # entry likes
        entry.like_count = Like.objects.filter(object=entry_url).count()
        entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()

        # fetch comments
        entry.fetched_comments = Comment.objects.filter(entry=entry_url).order_by("published")

        # all objects liked by current user
        liked_objects = Like.objects.filter(author=user_fqid).values_list("object", flat=True)

        # extract UUIDs from liked objects
        liked_uuids = {
            obj.rstrip("/").split("/")[-1]
            for obj in liked_objects
        }

        for comment in entry.fetched_comments:
            comment_uuid = comment.id.rstrip("/").split("/")[-1]

            comment.like_count = Like.objects.filter(
                object__endswith=comment_uuid
            ).count()

            comment.liked_by_user = comment_uuid in liked_uuids

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


def my_entries(request):
    """
    Displays a list of entries created by the currently logged-in author, 
    ordered by publication date (newest first).
    """
    if not request.session.get("author_id"): 
        return redirect("/app/login")
    author = Author.objects.get(id=request.session["author_id"])

    # Get all entries by this author, ordered by newest first
    entries = Entry.objects.filter(author=author).order_by("-published")
    user_fqid = f"{request.build_absolute_uri('/')[:-1]}/authors/{author.id}"

    # Manually attach Like/Comment data for interactions
    for entry in entries:
        entry_url = f"{request.build_absolute_uri('/')[:-1]}/app/entry/{entry.id}/"
        
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

    entries = (Entry.objects.filter(author=author).order_by("-published"))

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

    user_fqid = None
    if logged_in_id:
        user_fqid = f"{request.build_absolute_uri('/')[:-1]}/authors/{logged_in_id}"

    # Manually attach Like/Comment data for the interactions
    for entry in entries_list:
        entry_url = f"{request.build_absolute_uri('/')[:-1]}/app/entry/{entry.id}/"
        
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
    entry = get_object_or_404(Entry, id=entry_id)
    if "author_id" in request.session:
        logged_in_id = request.session.get("author_id")
        viewer = get_object_or_404(Author, id=logged_in_id)
        return render(
            request,
            "entries/entry.html",
            {"entry": entry, "allowed": entry.visibility in ["PUBLIC", "UNLISTED"] or viewer in entry.author.friends()},
        )
    return render(
        request,
        "entries/entry.html",
        {"entry": entry, "allowed": entry.visibility in ["PUBLIC", "UNLISTED"]},
    )