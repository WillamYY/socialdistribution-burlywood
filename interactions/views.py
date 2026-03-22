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
from django.http import JsonResponse
from urllib.parse import urlparse
from core.models import IncomingNode

def get_remote_node_for_url(target_url: str):
    """
    Match a remote URL like:
    https://remote-node.com/api/authors/1/entries/abc
    to an IncomingNode with url:
    https://remote-node.com/
    """
    normalized = (target_url or "").strip().replace("http://", "https://")
    parsed = urlparse(normalized)
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    return IncomingNode.objects.filter(url=origin).first()

def add_like(request, entry_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    author_id = request.session.get("author_id")
    if not author_id:
        return JsonResponse({"error": "Not logged in"}, status=401)

    entry = get_object_or_404(Entry, id=entry_id)
    base = request.build_absolute_uri('/')[:-1]
    entry_fqid = f"{base}/api/authors/{entry.author.id}/entries/{entry.id}"
    author_fqid = f"{base}/api/authors/{author_id}"

    like_id = uuid.uuid4()
    like, created = Like.objects.get_or_create(
        author=author_fqid,
        object=entry_fqid,
        defaults={'id': f"{base}/likes/{like_id}", "uuid": like_id}
    )

    if created:
        return JsonResponse({"success": True, "liked": True})
    else:
        like.delete()
        return JsonResponse({"success": True, "liked": False})

def add_remote_like(request, entry_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    author_id = request.session.get("author_id")
    if not author_id:
        return JsonResponse({"error": "Not logged in"}, status=401)

    remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")
    base = request.build_absolute_uri("/").rstrip("/").replace("http://", "https://")

    author = get_object_or_404(Author, pk=author_id)
    author_fqid = f"{base}/api/authors/{author.id}"

    remote_node = get_remote_node_for_url(remote_entry_url)
    print("REMOTE ENTRY URL:", remote_entry_url)
    print("MATCHED NODE URL:", remote_node.url if remote_node else None)
    print("MATCHED NODE USERNAME:", remote_node.username if remote_node else None)
    print("MATCHED NODE PASSWORD:", remote_node.password if remote_node else None)

    if not remote_node:
        print("NO MATCHING REMOTE NODE FOR:", remote_entry_url)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    try:
        print("AUTH SENT:", (remote_node.username, remote_node.password) if remote_node else None)
        entry_resp = requests.get(
            remote_entry_url,
            headers={"Accept": "application/json"},
            auth=(remote_node.username, remote_node.password),
            timeout=10,
        )
        print("REMOTE ENTRY FETCH STATUS:", entry_resp.status_code)
        print("REMOTE ENTRY FETCH BODY:", entry_resp.text[:500])
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()
    except requests.RequestException as e:
        print("REMOTE ENTRY FETCH FAILED:", str(e))
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    foreign_author = (entry_data.get("author") or {}).get("id")
    if not foreign_author:
        print("REMOTE ENTRY HAS NO AUTHOR ID:", entry_data)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    inbox_url = foreign_author.rstrip("/") + "/inbox"

    like_id = uuid.uuid4()
    like_fqid = f"{base}/likes/{like_id}"

    author_info = {
        "type": "author",
        "id": author_fqid,
        "host": base,
        "displayName": author.name,
        "github": author.github,
        "profileImage": getattr(author, "picture_url", "") or "",
        "web": getattr(author, "web", "") or "",
    }

    payload = {
        "type": "Like",
        "author": author_info,
        "published": datetime.now().isoformat(),
        "id": like_fqid,
        "object": remote_entry_url,
    }

    try:
        resp = requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(remote_node.username, remote_node.password),
            timeout=10,
        )
        print("REMOTE LIKE STATUS:", resp.status_code)
        print("REMOTE LIKE BODY:", resp.text[:500])
        resp.raise_for_status()
    except requests.RequestException as e:
        print("REMOTE LIKE POST FAILED:", str(e))
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    like, created = Like.objects.get_or_create(
        author=author_fqid,
        object=remote_entry_url,
        defaults={
            "id": like_fqid,
            "uuid": like_id,
        },
    )

    if not created:
        # Optional toggle behavior locally.
        # If the remote node does not support unlike, this only affects your local copy.
        like.delete()

    return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

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
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    author_id = request.session.get("author_id")
    if not author_id:
        return JsonResponse({"error": "Not logged in"}, status=401)

    comment_text = (request.POST.get("comment") or "").strip()
    if not comment_text:
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")
    base = request.build_absolute_uri("/").rstrip("/").replace("http://", "https://")

    author = get_object_or_404(Author, pk=author_id)
    author_fqid = f"{base}/api/authors/{author.id}"

    remote_node = get_remote_node_for_url(remote_entry_url)
    print("REMOTE ENTRY URL:", remote_entry_url)
    print("MATCHED NODE URL:", remote_node.url if remote_node else None)
    print("MATCHED NODE USERNAME:", remote_node.username if remote_node else None)
    print("MATCHED NODE PASSWORD:", remote_node.password if remote_node else None)

    if not remote_node:
        print("NO MATCHING REMOTE NODE FOR:", remote_entry_url)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    try:
        print("AUTH SENT:", (remote_node.username, remote_node.password) if remote_node else None)
        entry_resp = requests.get(
            remote_entry_url,
            headers={"Accept": "application/json"},
            auth=(remote_node.username, remote_node.password),
            timeout=10,
        )
        print("REMOTE ENTRY FETCH STATUS:", entry_resp.status_code)
        print("REMOTE ENTRY FETCH BODY:", entry_resp.text[:500])
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()
    except requests.RequestException as e:
        print("REMOTE ENTRY FETCH FAILED:", str(e))
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    foreign_author = (entry_data.get("author") or {}).get("id")
    if not foreign_author:
        print("REMOTE ENTRY HAS NO AUTHOR ID:", entry_data)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    inbox_url = foreign_author.rstrip("/") + "/inbox"

    comment_uuid = uuid.uuid4()
    comment_fqid = f"{base}/comments/{comment_uuid}"

    author_info = {
        "type": "author",
        "id": author_fqid,
        "host": base,
        "displayName": author.name,
        "github": author.github,
        "profileImage": getattr(author, "picture_url", "") or "",
        "web": getattr(author, "web", "") or "",
    }

    payload = {
        "type": "comment",
        "author": author_info,
        "comment": comment_text,
        "contentType": "text/plain",
        "id": comment_fqid,
        "published": datetime.now().isoformat(),
        "entry": remote_entry_url,
        "object": remote_entry_url,
    }

    try:
        resp = requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(remote_node.username, remote_node.password),
            timeout=10,
        )
        print("REMOTE COMMENT STATUS:", resp.status_code)
        print("REMOTE COMMENT BODY:", resp.text[:500])
        resp.raise_for_status()
    except requests.RequestException as e:
        print("REMOTE COMMENT POST FAILED:", str(e))
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    Comment.objects.create(
        id=comment_fqid,
        author=author_fqid,
        entry=remote_entry_url,
        comment=comment_text,
        contentType="text/plain",
    )

    return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

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