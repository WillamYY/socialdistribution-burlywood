import base64
import markdown
import bleach
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count
from .models import Entry, Like
from core.models import Author

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
    
    return render(request, "entries/my_entries.html", {"entries": entries})

def view_entries(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    logged_in_id = request.session.get('author_id')
    is_owner = logged_in_id == author.id

    entries = Entry.objects.filter(author=author).order_by('-published')
    entries = Entry.objects.annotate(likeCount = Count("like")) # Attaches a likeCount value to every entry

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
    # owner sees all entries, including UNLISTED
    return render(request, 'entries/view_entries.html', {
        'author': author,
        'entries': entries,
    })

def like_entry(request,author_id,entry_id):
    if request.session.get('author_id'):
        entry = get_object_or_404(Entry,id = entry_id) # Gets the entry being liked
        author = get_object_or_404(Author,id = request.session.get('author_id')) # Gets the author liking the entry
        # Clicking like button when you have already liked it leads to removing the like
        if Like.objects.filter(entry = entry, user = author).exists():
            Like.objects.get(entry = entry, user = author).delete()
        # Creates a like if it has not already been liked
        else:
            like = Like(entry = entry,user = author)
            like.save()
        return redirect("view_entries",author_id)
    # Returns a redirect immediately if there is no author signed in
    else:
        return redirect("view_entries",author_id)
    
def get_entry(request, entry_id):
    logged_in_id = request.session.get('author_id')
    viewer = get_object_or_404(Author, id=logged_in_id)
    entry = get_object_or_404(Entry, id = entry_id)
    return render(request, "entries/entry.html", {"entry": entry, "allowed": entry.visibility in ["PUBLIC", "UNLISTED"] or viewer in entry.author.friends()})
