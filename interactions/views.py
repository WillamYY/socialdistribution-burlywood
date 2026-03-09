import uuid
from django.shortcuts import redirect, get_object_or_404
from .models import Like, Comment
from entries.models import Entry

def add_like(request, entry_id):
    """Toggles a Like object using the Entry's FQID (URL)."""
    if request.method == "POST":
        author_id = request.session.get("author_id")

        if not author_id:
            return redirect('/app/login/') 
            
        entry = get_object_or_404(Entry, id=entry_id)
        entry_fqid = f"{request.build_absolute_uri('/')[:-1]}/app/entry/{entry.id}/"
        author_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}"

        likeId = uuid.uuid4()
        like, created = Like.objects.get_or_create(
            author=author_fqid,
            object=entry_fqid,
            defaults={'id': f"{request.build_absolute_uri('/')[:-1]}/likes/{likeId}","uuid":likeId}
        )

        if not created:
            like.delete()

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))


def add_comment(request, entry_id):
    """Creates a Comment object using the Entry's FQID (URL)."""
    if request.method == "POST":
        author_id = request.session.get("author_id")
        
        if not author_id:
            return redirect('/app/login/')

        entry = get_object_or_404(Entry, id=entry_id)
        comment_text = request.POST.get("comment")
        
        if comment_text:
            entry_fqid = f"{request.build_absolute_uri('/')[:-1]}/app/entry/{entry.id}/"
            author_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}"

            Comment.objects.create(
                id=f"{request.build_absolute_uri('/')[:-1]}/comments/{uuid.uuid4()}",
                author=author_fqid,
                entry=entry_fqid,
                comment=comment_text,
                contentType="text/plain"
            )

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

def add_comment_like(request, comment_id):
    """Toggle Like on a Comment object."""
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')

        base = request.build_absolute_uri('/')[:-1]

        # rebuild the stored comment ID
        full_comment_id = f"{base}/comments/{comment_id}"

        comment = get_object_or_404(Comment, id=full_comment_id)

        comment_fqid = full_comment_id
        author_fqid = f"{base}/api/authors/{author_id}"

        likeId = uuid.uuid4()
        like, created = Like.objects.get_or_create(
            author=author_fqid,
            object=comment_fqid,
            defaults={'id': f"{base}/likes/{likeId}","uuid":likeId}
        )

        if not created:
            like.delete()

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))