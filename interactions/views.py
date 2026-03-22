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

def add_like(request, entry_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    author_id = request.session.get("author_id")
    if not author_id:
        return JsonResponse({"success": False, "error": "Login required"}, status=403)

    me = get_object_or_404(Author, id=author_id)
    entry = get_object_or_404(Entry, id=entry_id)

    object_fqid = f"{entry.author.host}/authors/{entry.author.id}/entries/{entry.id}".rstrip("/")
    author_fqid = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{me.id}".rstrip("/")

    existing = Like.objects.filter(
        object__in=[object_fqid, object_fqid + "/"],
        author__in=[author_fqid, author_fqid + "/"]
    ).first()

    if existing:
        existing.delete()
        return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

    print(object_fqid)
    like = Like(object=object_fqid, author=author_fqid)
    like.uuid = uuid.uuid4()
    like.id = author_fqid +  "/liked/" + str(like.uuid)
    like.save()

    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))
    
def add_remote_like(request, entry_id):
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')
        # Gets the entry info and ensures its valid
        entryInfo = requests.get(entry_id.rstrip("/"))
        entryInfo.raise_for_status()
        jsonEntry = json.loads(entryInfo.text)
        foreignAuthor = jsonEntry["author"]["id"]
        # Get author making request
        entry_id = entry_id.replace("http","https")
        author = get_object_or_404(Author, pk = author_id)
        # Print the likes
        print(jsonEntry["likes"]["count"])
        authorInfo = {"type":"author","id": author.host + "/authors/" + str(author.id),"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web}
        # Post the like to the inbox
        post = requests.post(foreignAuthor + "/inbox",json = {"type": "like","author": authorInfo,"published":datetime.now().isoformat(),"id":"","object":entry_id})

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
    if request.method != "POST":
        return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

    author_id = request.session.get("author_id")
    if not author_id:
        return redirect('/app/login/')

    comment_text = (request.POST.get("comment") or "").strip()
    if not comment_text:
        return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

    remote_entry_url = entry_id.rstrip("/").replace("http://", "https://")
    base = request.build_absolute_uri('/')[:-1].replace("http://", "https://")
    author = get_object_or_404(Author, pk=author_id)
    author_fqid = f"{base}/api/authors/{author.id}"

    try:
        entry_resp = requests.get(
            remote_entry_url,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()
    except requests.RequestException as e:
        print("REMOTE COMMENT GET ERROR:", e)
        return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

    foreign_author = (entry_data.get("author") or {}).get("id")
    if not foreign_author:
        print("REMOTE COMMENT ERROR: no foreign author id")
        return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

    author_info = {
        "type": "author",
        "id": author_fqid,
        "host": f"{base}/api",
        "displayName": author.name,
        "github": author.github,
        "profileImage": getattr(author, "picture_url", "") or "",
        "web": author.web,
    }

    inbox_url = foreign_author.rstrip("/") + "/inbox"

    payload = {
        "type": "comment",
        "author": author_info,
        "comment": comment_text,
        "contentType": "text/plain",
        "object": remote_entry_url,
        "id": f"{base}/comments/{uuid.uuid4()}",
        "published": datetime.now().isoformat(),
    }

    try:
        resp = requests.post(
            inbox_url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        print("REMOTE COMMENT POST STATUS:", resp.status_code)
        print("REMOTE COMMENT POST BODY:", resp.text)

        if resp.status_code in (200, 201, 202):
            Comment.objects.create(
                id=payload["id"],
                author=author_fqid,
                entry=remote_entry_url,
                comment=comment_text,
                contentType="text/plain",
            )
        else:
            print("REMOTE COMMENT FAILED")
    except requests.RequestException as e:
        print("REMOTE COMMENT POST ERROR:", e)

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