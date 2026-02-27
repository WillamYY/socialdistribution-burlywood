import uuid
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone

from core.models import Author
from entries.models import Entry
from .models import Comment, Like

@require_POST
def create_comment(request, author_id, entry_id):
    """
    Handles creation of a comment for a specific entry by a logged-in author.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")
    
    commenting_author = get_object_or_404(Author, id=request.session["author_id"])
    entry = get_object_or_404(Entry, id=entry_id)

    comment_text = request.POST.get("comment", "").strip()
    content_type = request.POST.get("contentType", "text/plain")

    if comment_text:
        host = request.get_host()
        author_fqid = f"http://{host}/api/authors/{commenting_author.id}"
        entry_fqid = f"http://{host}/api/authors/{author_id}/entries/{entry_id}"
        
        # Generate a new unique ID for this specific comment
        comment_uuid = str(uuid.uuid4())
        comment_fqid = f"{entry_fqid}/comments/{comment_uuid}"

        # Save using the new FQID fields
        new_comment = Comment(
            id=comment_fqid,
            entry=entry_fqid,
            author=author_fqid,
            comment=comment_text,
            contentType=content_type,
            published=timezone.now()
        )
        new_comment.save()
    return redirect(request.META.get('HTTP_REFERER', '/app/my-entries/'))

@require_POST
def toggle_like_comment(request, comment_id):
    """
    Toggle a like/unlike on a comment by the logged-in author.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    liking_author = get_object_or_404(Author, id=request.session["author_id"])
    host = request.get_host()
    
    author_fqid = f"http://{host}/api/authors/{liking_author.id}"
    comment_fqid = comment_id

    # Check if this exact author has already liked this exact comment
    existing_like = Like.objects.filter(author=author_fqid, object=comment_fqid).first()

    if existing_like:
        existing_like.delete()
    else:
        like_uuid = str(uuid.uuid4())
        like_fqid = f"{author_fqid}/liked/{like_uuid}"
        
        new_like = Like(
            id=like_fqid,
            author=author_fqid,
            object=comment_fqid,
            published=timezone.now()
        )
        new_like.save()
    return redirect(request.META.get('HTTP_REFERER', '/app/my-entries/'))

@require_POST
def like_entry(request, author_id, entry_id):
    """
    Toggle a like/unlike on an entry by the logged-in author.
    """
    if not request.session.get("author_id"):
        return redirect("/app/login")

    liking_author = get_object_or_404(Author, id=request.session["author_id"])
    host = request.get_host()

    author_fqid = f"http://{host}/api/authors/{liking_author.id}"
    entry_fqid = f"http://{host}/api/authors/{author_id}/entries/{entry_id}"

    # Check if this exact author has already liked this exact entry
    existing_like = Like.objects.filter(author=author_fqid, object=entry_fqid).first()

    if existing_like:
        existing_like.delete()
    else:
        like_uuid = str(uuid.uuid4())
        like_fqid = f"{author_fqid}/liked/{like_uuid}"
        
        new_like = Like(
            id=like_fqid,
            author=author_fqid,
            object=entry_fqid,
            published=timezone.now()
        )
        new_like.save()
    return redirect(request.META.get('HTTP_REFERER', '/app/my-entries/'))
