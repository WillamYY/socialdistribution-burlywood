from email.mime import base
from urllib import request
import uuid
from django.shortcuts import redirect, get_object_or_404
from .models import Like, Comment
from entries.models import Entry
from core.models import Author
import requests
from datetime import datetime
import json

def add_like(request, entry_id):
    """Toggles a Like object using the Entry's FQID (URL)."""
    if request.method == "POST":
        author_id = request.session.get("author_id")

        if not author_id:
            return redirect('/app/login/') 
            
        entry = get_object_or_404(Entry, id=entry_id)
        base = request.build_absolute_uri('/')[:-1]
        entry_fqid = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
        author_fqid = f"{base}/api/authors/{request.session['author_id']}"

        likeId = uuid.uuid4()
        like, created = Like.objects.get_or_create(
            author=author_fqid,
            object=entry_fqid,
            defaults={'id': f"{request.build_absolute_uri('/')[:-1]}/likes/{likeId}","uuid":likeId}
        )
        if not created:
            like.delete()

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

def add_remote_like(request, entry_id):
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')

        remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")

        try:
            entry_resp = requests.get(
                remote_entry_url,
                headers={"Accept": "application/json"},
                timeout=10,
            )
            entry_resp.raise_for_status()
            entry_data = entry_resp.json()
        except requests.RequestException:
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        foreign_author = (entry_data.get("author") or {}).get("id")
        if not foreign_author:
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        author = get_object_or_404(Author, pk=author_id)
        base = request.build_absolute_uri('/')[:-1]

        author_info = {
            "type": "author",
            "id": f"{base}/api/authors/{author.id}",
            "host": f"{base}/api",
            "displayName": author.name,
            "github": author.github,
            "profileImage": getattr(author, "picture_url", "") or "",
            "web": author.web,
        }

        inbox_url = foreign_author.rstrip("/") + "/inbox"

        try:
            requests.post(
                inbox_url,
                json={
                    "type": "like",
                    "author": author_info,
                    "published": datetime.now().isoformat(),
                    "id": "",
                    "object": remote_entry_url,
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException:
            pass

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
            base = request.build_absolute_uri('/')[:-1]
            entry_fqid = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
            author_fqid = f"{base}/api/authors/{author_id}"

            Comment.objects.create(
                id=f"{request.build_absolute_uri('/')[:-1]}/comments/{uuid.uuid4()}",
                author=author_fqid,
                entry=entry_fqid,
                comment=comment_text,
                contentType="text/plain"
            )

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

def add_remote_comment(request, entry_id):
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')

        comment_text = (request.POST.get("comment") or "").strip()
        if not comment_text:
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")

        try:
            entry_resp = requests.get(
                remote_entry_url,
                headers={"Accept": "application/json"},
                timeout=10,
            )
            entry_resp.raise_for_status()
            entry_data = entry_resp.json()
        except requests.RequestException:
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        foreign_author = (entry_data.get("author") or {}).get("id")
        if not foreign_author:
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        author = get_object_or_404(Author, pk=author_id)
        base = request.build_absolute_uri('/')[:-1]

        author_info = {
            "type": "author",
            "id": f"{base}/api/authors/{author.id}",
            "host": f"{base}/api",
            "displayName": author.name,
            "github": author.github,
            "profileImage": getattr(author, "picture_url", "") or "",
            "web": author.web,
        }

        inbox_url = foreign_author.rstrip("/") + "/inbox"

        try:
            requests.post(
                inbox_url,
                json={
                    "type": "comment",
                    "author": author_info,
                    "comment": comment_text,
                    "contentType": "text/plain",
                    "object": remote_entry_url,
                    "entry": remote_entry_url,
                    "published": datetime.now().isoformat(),
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException:
            pass

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

def add_comment_like(request, comment_id):
    """Toggle Like on a Comment object."""
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')

        base = request.build_absolute_uri('/')[:-1]

        comment = get_object_or_404(Comment, id__endswith=comment_id)

        comment_fqid = comment.id
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
