from email.mime import base
from platform import node
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
from django.conf import settings
from core.models import IncomingNode

def get_remote_node_for_url(url: str):
    normalized = url.rstrip("/").replace("http://", "https://")
    for node in IncomingNode.objects.all():
        node_url = node.url.rstrip("/").replace("http://", "https://")
        if normalized.startswith(node_url):
            return node
    return None

def build_local_author_payload(author, base: str):
    return {
        "type": "author",
        "id": f"{base}/api/authors/{author.id}",
        "host": f"{base}/api",
        "displayName": author.name,
        "github": getattr(author, "github", "") or "",
        "profileImage": getattr(author, "picture_url", "") or "",
        "web": getattr(author, "web", "") or "",
    }

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

    like_uuid = uuid.uuid4()
    like_fqid = f"{base}/likes/{like_uuid}"

    like, created = Like.objects.get_or_create(
        author=author_fqid,
        object=remote_entry_url,
        defaults={
            "id": like_fqid,
            "uuid": like_uuid,
        }
    )

    # toggle off locally
    if not created:
        like.delete()
        return JsonResponse({"success": True, "liked": False})

    try:
        entry_resp = requests.get(
            remote_entry_url,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        print("REMOTE ENTRY GET URL:", remote_entry_url)
        print("REMOTE ENTRY GET STATUS:", entry_resp.status_code)
        print("REMOTE ENTRY GET TEXT:", entry_resp.text[:500])
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()
    except requests.RequestException as e:
        print("REMOTE ENTRY GET ERROR:", str(e))
        like.delete()
        return JsonResponse({"success": False, "error": "Could not fetch remote entry"}, status=502)

    foreign_author = (entry_data.get("author") or {}).get("id")
    if not foreign_author:
        print("REMOTE ENTRY AUTHOR FIELD MISSING:", entry_data)
        like.delete()
        return JsonResponse({"success": False, "error": "Remote entry missing author id"}, status=502)

    foreign_author = foreign_author.rstrip("/").replace("http://", "https://")
    inbox_url = f"{foreign_author}/inbox"
    node = get_remote_node_for_url(inbox_url)

    print("MATCHED NODE URL:", node.url if node else None)
    print("MATCHED NODE USERNAME:", node.username if node else None)
    print("REMOTE INBOX URL FINAL:", inbox_url)

    if not node:
        print("NO MATCHING INCOMINGNODE FOR:", remote_entry_url)
        like.delete()
        return JsonResponse({"success": False, "error": "Remote node credentials not found"}, status=502)

    username = getattr(node, "username", None)
    password = getattr(node, "password", None)

    payload = {
        "type": "Like",
        "author": build_local_author_payload(author, base),
        "published": datetime.now().isoformat(),
        "id": like_fqid,
        "object": remote_entry_url,
    }

    try:
        resp = requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(username, password),
            timeout=10,
        )
        print("REMOTE LIKE INBOX URL:", inbox_url)
        print("REMOTE LIKE PAYLOAD:", payload)
        print("REMOTE LIKE STATUS:", resp.status_code)
        print("REMOTE LIKE TEXT:", resp.text[:500])
        resp.raise_for_status()
    except requests.RequestException as e:
        print("REMOTE LIKE ERROR:", str(e))
        like.delete()
        return JsonResponse({"success": False, "error": "Remote like delivery failed"}, status=502)

    return JsonResponse({"success": True, "liked": True})

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
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    author_id = request.session.get("author_id")
    if not author_id:
        return redirect("/app/login/")

    comment_text = (request.POST.get("comment") or "").strip()
    if not comment_text:
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")
    base = request.build_absolute_uri("/").rstrip("/").replace("http://", "https://")
    author = get_object_or_404(Author, pk=author_id)
    author_fqid = f"{base}/api/authors/{author.id}"

    comment_uuid = uuid.uuid4()
    comment_fqid = f"{base}/comments/{comment_uuid}"

    try:
        entry_resp = requests.get(
            remote_entry_url,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        print("REMOTE ENTRY GET URL:", remote_entry_url)
        print("REMOTE ENTRY GET STATUS:", entry_resp.status_code)
        print("REMOTE ENTRY GET TEXT:", entry_resp.text[:500])
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()
    except requests.RequestException as e:
        print("REMOTE ENTRY GET ERROR:", str(e))
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    foreign_author = (entry_data.get("author") or {}).get("id")
    if not foreign_author:
        print("REMOTE ENTRY AUTHOR FIELD MISSING:", entry_data)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    foreign_author = foreign_author.rstrip("/").replace("http://", "https://")
    inbox_url = f"{foreign_author}/inbox"
    node = get_remote_node_for_url(inbox_url)

    print("MATCHED NODE URL:", node.url if node else None)
    print("MATCHED NODE USERNAME:", node.username if node else None)
    print("REMOTE INBOX URL FINAL:", inbox_url)

    if not node:
        print("NO MATCHING INCOMINGNODE FOR:", remote_entry_url)
        return redirect(request.META.get("HTTP_REFERER", "/app/stream/"))

    username = getattr(node, "username", None)
    password = getattr(node, "password", None)

    payload = {
        "type": "Comment",
        "author": build_local_author_payload(author, base),
        "comment": comment_text,
        "contentType": "text/plain",
        "object": remote_entry_url,
        "id": comment_fqid,
        "published": datetime.now().isoformat(),
    }

    try:
        resp = requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(username, password),
            timeout=10,
        )
        print("REMOTE COMMENT INBOX URL:", inbox_url)
        print("REMOTE COMMENT PAYLOAD:", payload)
        print("REMOTE COMMENT STATUS:", resp.status_code)
        print("REMOTE COMMENT TEXT:", resp.text[:500])
        resp.raise_for_status()
    except requests.RequestException as e:
        print("REMOTE COMMENT ERROR:", str(e))
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
