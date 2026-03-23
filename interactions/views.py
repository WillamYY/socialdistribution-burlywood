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
import re

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
        # Gets the entry info and ensures its valid
        entryInfo = requests.get(entry_id.rstrip("/"))
        entryInfo.raise_for_status()
        jsonEntry = json.loads(entryInfo.text)
        foreignAuthor = jsonEntry["author"]["id"]
        # Get author making request
        if "https" not in entry_id:
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
                id=f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}/commented/{uuid.uuid4()}",
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

        # normalize remote entry url
        remote_entry_url = entry_id.rstrip("/")
        if "https" not in remote_entry_url:
            remote_entry_url = remote_entry_url.replace("http", "https")

        author = get_object_or_404(Author, pk=author_id)

        # keep a local copy so your side can still display it
        base = request.build_absolute_uri('/')[:-1].replace("http://", "https://")
        local_author_fqid = f"{base}/api/authors/{author.id}"
        try:
            # get remote entry first, same pattern as remote like
            entry_resp = requests.get(
                remote_entry_url,
                headers={"Accept": "application/json"},
                timeout=10,
            )
            entry_resp.raise_for_status()
            entry_data = entry_resp.json()
            foreign_author = entry_data["author"]["id"]
        except Exception as e:
            print("REMOTE COMMENT ENTRY FETCH ERROR:", str(e))
            return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))

        # build author info in the same style as add_remote_like
        author_info = {
            "type": "author",
            "id": author.host + "/authors/" + str(author.id),
            "host": author.host,
            "displayName": author.name,
            "github": author.github,
            "profileImage": author.picture_url,
            "web": author.web,
        }

        payload = {
            "type": "comment",
            "author": author_info,
            "published": datetime.now().isoformat(),
            "id": f"{entry_data["author"]["host"]}/api/authors/{author_id}/commented/{uuid.uuid4()}",
            "comment": comment_text,
            "contentType": "text/plain",
            "object": remote_entry_url,
        }

        try:
            resp = requests.post(
                foreign_author.rstrip("/") + "/inbox",
                json=payload,
                timeout=10,
            )
            print("REMOTE COMMENT POST STATUS:", resp.status_code)
            print("REMOTE COMMENT POST BODY:", resp.text)
        except Exception as e:
            print("REMOTE COMMENT POST ERROR:", str(e))

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

def add_remote_comment_like(request, comment_id):
    if request.method == "POST":
        author_id = request.session.get("author_id")
        if not author_id:
            return redirect('/app/login/')
        # Gets the entry info and ensures its valid
        commentInfo = requests.get(re.match("(https?://[^/]+)",comment_id).group(1) + "/api/commented/" + comment_id)
        commentInfo.raise_for_status()
        jsonEntry = json.loads(commentInfo.text)
        foreignAuthor = jsonEntry["author"]["id"]
        # Get author making request
        if "https" not in comment_id:
            comment_id = comment_id.replace("http","https")
        author = get_object_or_404(Author, pk = author_id)
        authorInfo = {"type":"author","id": author.host + "/authors/" + str(author.id),"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web}
        # Post the like to the inbox
        post = requests.post(foreignAuthor + "/inbox",json = {"type": "like","author": authorInfo,"published":datetime.now().isoformat(),"id":"","object":comment_id})