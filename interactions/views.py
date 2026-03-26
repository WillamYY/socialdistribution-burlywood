from email.mime import base
from urllib import request
import uuid
from django.shortcuts import redirect, get_object_or_404
from .models import Like, Comment
from entries.models import Entry
from core.models import Author, IncomingNode
import requests
from datetime import datetime
import json
import re
from django.http import JsonResponse
from api.views import _inbox_handle_comment_like

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
            defaults={'id': f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}/liked/{likeId}","uuid":likeId}
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
        host = entry_id[:entry_id.index("api/")]
        remotenode = IncomingNode.objects.get(url = host)
        auth = (remotenode.username,remotenode.password)
        print(auth)
        entryInfo = requests.get(entry_id.rstrip("/"), auth=auth)
        entryInfo.raise_for_status()
        jsonEntry = json.loads(entryInfo.text)
        foreignAuthor = jsonEntry["author"]["id"]
        # Get author making request
        if "https" not in entry_id:
            entry_id = entry_id.replace("http","https")
        author = get_object_or_404(Author, pk = author_id)
        # Print the likes
        print(jsonEntry["likes"]["count"])
        host = (author.host or "").rstrip("/")
        if not host.endswith("/api"):
            host = f"{host}/api"

        authorInfo = {
            "type": "author",
            "id": f"{host}/authors/{author.id}",
            "host": host,
            "displayName": author.name or author.username,
            "github": author.github,
            "profileImage": author.picture_url,
            "web": author.web,
        }
        like_uuid = uuid.uuid4()
        like, created = Like.objects.get_or_create(
            author=authorInfo["id"],
            object=entry_id,
            defaults={'id': f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}/liked/{like_uuid}","uuid":like_uuid}
        )
        if not created:
            like.delete()
        # Post the like to the inbox
        credentials = get_object_or_404(IncomingNode, url = foreignAuthor[:foreignAuthor.index("/api")] + "/")
        post = requests.post(foreignAuthor + "/inbox",json = {"type": "like","author": authorInfo,"published":datetime.now().isoformat(),"id":f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}/liked/{like_uuid}","object":entry_id}, auth=(credentials.username, credentials.password))

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
            credentials = get_object_or_404(IncomingNode, url = remote_entry_url[:remote_entry_url.index("/api")] + "/")
            entry_resp = requests.get(
                remote_entry_url,
                headers={"Accept": "application/json"},
                timeout=10,
                auth=(credentials.username, credentials.password)
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
            "id": local_author_fqid,
            "host": author.host,
            "displayName": author.name or author.username,
            "github": author.github,
            "profileImage": author.picture_url,
            "web": author.web,
        }
        comment_uuid = uuid.uuid4()
        id = f"{request.build_absolute_uri('/')[:-1]}/api/authors/{author_id}/commented/{comment_uuid}"
        payload = {
            "type": "comment",
            "author": author_info,
            "published": datetime.now().isoformat(),
            "id": id,
            "comment": comment_text,
            "contentType": "text/plain",
            "object": remote_entry_url,
        }
        print("SESSION AUTHOR_ID:", author_id)
        print("LOCAL AUTHOR OBJ ID:", author.id)
        print("LOCAL AUTHOR USERNAME:", author.username)
        print("LOCAL AUTHOR NAME:", author.name)
        print("LOCAL AUTHOR HOST:", author.host)
        print("REMOTE COMMENT PAYLOAD AUTHOR:", payload["author"])
        print("REMOTE COMMENT FULL PAYLOAD:", payload)
        try:
            credentials = get_object_or_404(IncomingNode, url = foreign_author[:foreign_author.index("/api")] + "/")
            resp = requests.post(
                foreign_author.rstrip("/") + "/inbox",
                json=payload,
                timeout=10,
                auth=(credentials.username, credentials.password)
            )
            print("REMOTE COMMENT POST STATUS:", resp.status_code)
            # Only add it to our database if it was successful
            if 200 <= resp.status_code < 300:
                Comment.objects.create(
                    id=id,
                    author=local_author_fqid,
                    entry=remote_entry_url,
                    comment=comment_text,
                    contentType="text/plain"
                ).save()
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
        author = get_object_or_404(Author,id = author_id)
        # Creates the author Info so both paths can use it
        authorInfo = {
                "type": "author",
                "id": f"{author.host}/authors/{author.id}",
                "host": author.host,
                "displayName": author.name or author.username,
                "github": author.github,
                "profileImage": author.picture_url,
                "web": author.web,
            }
        # Gets the host that has the comment
        host = re.match("https?://([^/]+)",comment_id).group(1)
        # Gets the author of a comment
        if host == request.get_host():
            print(comment_id)
            print("THIS IS TRUE")
            author_fqid = Comment.objects.get(id__endswith = re.search("/commented/([^/]+)",comment_id).group(1)).author
            print(author_fqid)
            # Gets the json for the like
            likejson = {"type": "like","author": authorInfo,"published":datetime.now().isoformat(),"id":"","object":comment_id}
            # Replaces whatever the scheme of the author is with the current scheme (Useful when running local host)
            author_fqid = re.sub("https?",request.scheme,author_fqid)
            # Calls the inbox directly if it is a local authors comment
            _inbox_handle_comment_like(request,author_fqid,likejson)
        else:
            # Gets the comment if it was made by a remote author
            print(re.match("https?://[^/]+",comment_id).group(0))
            remotenode = IncomingNode.objects.get(url = re.match("https?://[^/]+",comment_id).group(0) + "/")
            auth = (remotenode.username,remotenode.password)
            commentInfo = requests.get(comment_id.rstrip("/"), auth=auth)
            commentInfo.raise_for_status()
            jsoncomment = json.loads(commentInfo.text)
            author_fqid = jsoncomment["author"]["id"]
            # Post the like to the inbox
            print(author_fqid[:author_fqid.index("/api")] + "/")
            post = requests.post(author_fqid + "/inbox",json = {"type": "like","author": authorInfo,"published":datetime.now().isoformat(),"id":"","object":comment_id}, auth=auth)
    return redirect(request.META.get('HTTP_REFERER', '/app/stream/'))