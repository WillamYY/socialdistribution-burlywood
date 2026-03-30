import base64
import re
import markdown
import bleach
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, resolve, Resolver404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from .models import Entry
from core.models import Author, AdminHostedImage
from core.services import maybe_sync_github_for_stream
from core.remote import federate_entry_create_or_update, federate_entry_deleted
from interactions.models import Like, Comment
from core.models import RemoteFollow, RemoteFollower, IncomingNode
import requests
import json
from api.serializers import CommentSerializer
from django.utils import timezone


logger = logging.getLogger(__name__)

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

    # Public entries from IncomingNode; UNLISTED from following; FRIENDS from remote friends (mutual follow)
    from core.models import RemoteFollow, RemoteFollower
    from core.remote import fetch_remote_public_entries
    following_remote = RemoteFollow.objects.filter(follower=viewer)
    following_remote_fqids = []
    for following in following_remote:
        remote_host = following.followed_fqid[:following.followed_fqid.index("/api")] + "/"
        credentials = IncomingNode.objects.get(url = remote_host)
        code = requests.get(
            f"{following.followed_fqid}/followers/{viewer.id}",
            headers={"Accept": "application/json"},
            auth=(credentials.username, credentials.password),
            timeout=10
        )
        if code < 400:
            following_remote_fqids.append(following)

    """ following_remote_fqids = list(
        RemoteFollow.objects.filter(follower=viewer).values_list("followed_fqid", flat=True)
    ) """
    # Remote friends = we follow them AND they follow us
    followers_remote_fqids = set(
        RemoteFollower.objects.filter(target=viewer).values_list("actor_fqid", flat=True)
    )
    friends_remote_fqids = [f for f in following_remote_fqids if f in followers_remote_fqids]
    base_url_for_fetch = request.build_absolute_uri("/")[:-1]
    viewer_fqid = f"{base_url_for_fetch}/api/authors/{viewer.id}"
    remote_entries = fetch_remote_public_entries(
        following_remote_fqids=following_remote_fqids,
        friends_remote_fqids=friends_remote_fqids,
        requested_by_fqid=viewer_fqid,
    )
    logger.info("STREAM VIEW viewer=%s local_entries=%s remote_entries=%s", viewer.id, len(local_entries), len(remote_entries))

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
            if "author_id" in request.session:
                partial_fqid = f"{request.get_host()}/api/authors/{request.session['author_id']}"
                entry.liked_by_user = Like.objects.filter(object__endswith= re.search("/entries/([^/]+)",entry.id).group(1), author__endswith = partial_fqid).exists()
            # Handles turning content into markdown
            if "markdown" in entry.contentType:
                entry.markdown = render_safe_markdown(entry.content)
            if "hhh" in entry.title:
                print(entry)
            continue
        else:
            entry_url = f"{base_url}/api/authors/{entry.author.id}/entries/{entry.id}"
        
            # Fetch the count of interactions
            entry.comment_count = Comment.objects.filter(entry__endswith=entry.id).count()
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
        entry.fetched_comments = Comment.objects.filter(entry__endswith=entry.id).order_by('published')

        # all objects liked by current user
        liked_objects = Like.objects.filter(author=user_fqid).values_list("object", flat=True)
        
        # extract UUIDs from liked objects
        liked_uuids = {
            obj.rstrip("/").split("/")[-1]
            for obj in liked_objects
        }

        for comment in entry.fetched_comments:
            # Extract commenter id from author URL (commenter = who wrote comment, NOT entry.author)
            match = re.search(r'/authors?/(\d+)/?$', comment.author)
            commenter_id = match.group(1) if match else comment.author.rstrip("/").split("/")[-1]

            try:
                commenter = Author.objects.get(id=commenter_id)
                comment.author_name = commenter.name or commenter.username
            except (Author.DoesNotExist, ValueError):
                comment.author_name = comment.author

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
    entry.fetched_comments = Comment.objects.filter(entry__endswith=entry.id).order_by('published')

    # Check if the logged-in user liked the this entry
    if logged_in_id:
        user_fqid = f"{base_url}/api/authors/{logged_in_id}"
        entry.liked_by_user = Like.objects.filter(object=entry_url, author=user_fqid).exists()
    else:
        entry.liked_by_user = False

    comments = []
    # Gets all the comments (Have to fetch each one individually :( )
    for comment in entry.fetched_comments:
        comment_id = comment.id
        comment_part_host = re.search("https?://([^/]+)",comment_id).group(1)
        # If it is our comment get it
        if comment_part_host == request.get_host():
            # Try and except incase the api returns faulty data
            try:
                comment = Comment.objects.get(id__endswith = re.search("/commented/([^/]+)",comment_id).group(0))
                serialized_comment = CommentSerializer(comment).data
                serialized_comment["local"] = True
                serialized_comment["like_count"] = Like.objects.filter(object=comment.id).count()
                comments.append(serialized_comment)
            except:
                pass
        else:
            # Tries to get the comment info (Passes if the comment is faulty or we don't have the host)
            try:
                comment_full_host = re.search("https?://[^/]+",comment_id).group(0)
                comment_node = IncomingNode.objects.get(url = comment_full_host + "/")
                comment_credentials = (comment_node.username,comment_node.password)
                comment_info = requests.get(comment_id,auth = comment_credentials)
                # If we failed to get the comment raise an error
                if comment_info.status_code >= 400:
                    raise ConnectionError
                comment_json = json.loads(comment_info.text)
                comment_json["local"] = False
                comment_json["like_count"] = comment_json["likes"]["count"]
                comments.append(comment_json)
            except:
                pass
    # Replaces the comments in the entry with the comments pulled from their respective databases
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
def RemoteEntry(request,fqid):
    # Handles hardcoded solutions variables
    fuschia = False
    if re.match("https?://socialdist-fuchsia-oabbasi-feef8b354ae5.herokuapp.com",fqid):
        fuschia = True
    # Gets where the host ends
    index = fqid.index("/api/")
    logged_in_id = request.session.get("author_id")
    # FORCES https for consistency
    fqid = re.sub("$https?://","https://",fqid)
    # Gets the entry
    node_credentials = get_object_or_404(IncomingNode, url=fqid[:index] + "/")
    entryInfo = requests.get(fqid.rstrip("/"), auth=(node_credentials.username, node_credentials.password))
    entryInfo.raise_for_status()
    entry = json.loads(entryInfo.text)
    # Creates the list of allowed things to view
    allowed_visibility = ["PUBLIC"]
    if RemoteFollow.objects.filter(follower = logged_in_id,followed_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1]).exists():
        is_following = RemoteFollow.objects.filter(follower = logged_in_id,followed_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1])
        remote_host = is_following.followed_fqid[:is_following.followed_fqid.index("/api")] + "/"
        credentials = IncomingNode.objects.get(url = remote_host)
        code = requests.get(
            f"{is_following.followed_fqid}/followers/{logged_in_id}",
            headers={"Accept": "application/json"},
            auth=(credentials.username, credentials.password),
            timeout=10
        )
        if code < 400:
            allowed_visibility.append("UNLISTED")
            if RemoteFollower.objects.filter(actor_fqid__endswith = entry.get("author").get("id").rstrip("/").split("/")[-1],target = logged_in_id).exists():
                allowed_visibility.append("FRIENDS")
        allowed = entry.get("visibility") in allowed_visibility
    comments = []
    # HARDCODE SOLUTION FOR fuschia
    if fuschia:
        entry["comments"] = {}
        entry["comments"]["src"] = entry.get("commentsSrc",{})
    # END HARDCODED SOLUTION
    entry_comments = entry.get("comments",{}).get("src",{})
    # Gets all the comments (Have to fetch each one individually :( )
    for comment in entry_comments:
        comment_id = comment.get("id")
        comment_part_host = re.search("https?://([^/]+)",comment_id).group(1)
        # If it is our comment get it
        if comment_part_host == request.get_host():
            # Try and except incase the api returns faulty data
            try:
                comment = Comment.objects.get(id__endswith = re.search("/commented/([^/]+)",comment_id).group(0))
                serialized_comment = CommentSerializer(comment).data
                serialized_comment["local"] = True
                serialized_comment["like_count"] = Like.objects.filter(object=comment.id).count()
                comments.append(serialized_comment)
            except:
                pass
        else:
            # Tries to get the comment info (Passes if the comment is faulty or we don't have the host)
            try:
                comment_full_host = re.search("https?://[^/]+",comment_id).group(0)
                comment_node = IncomingNode.objects.get(url = comment_full_host + "/")
                comment_credentials = (comment_node.username,comment_node.password)
                comment_info = requests.get(comment_id,auth = comment_credentials)
                # If we failed to get the comment raise an error
                if comment_info.status_code >= 400:
                    raise ConnectionError
                comment_json = json.loads(comment_info.text)
                comment_json["local"] = False
                comment_json["like_count"] = comment_json["likes"]["count"]
                comments.append(comment_json)
            except:
                pass
    # Replaces the comments in the entry with the comments pulled from their respective databases
    entry["comments"]["src"] = comments
    # Image api url
    image_api_url = None
    if ";base64" in entry.get("contentType") and "image" in entry.get("contentType"):
        image_api_url = fqid[:index] + "/api/entries/" + fqid + "/image"
    # Handles Markdown
    if "markdown" in entry.get("contentType"):
        entry["markdown"] = render_safe_markdown(entry.get("content"))
    # HARCODED SOLUTION FOR fuschia
    if fuschia:
        entry["like_count"] = entry.get("count",0)
    else:
        entry["like_count"] = entry.get("likes").get("count")
    entry["fetched_comments"] = entry.get("comments").get("src")

    return_url = request.session.get('last_feed_url', reverse('stream'))
    return render(request, "entries/remoteentry.html", {
        "entry": entry,
        "allowed": allowed,
        "return_url": return_url,
        "image_api_url": image_api_url,
    })