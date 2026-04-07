import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from urllib.parse import unquote
from core.models import Author, FollowRequest, RemoteFollower, RemoteFollow
from core.remote import _credentials_for_remote_author


def _author_to_json(author, request=None):
    """Build author JSON for API responses (User Story #69)."""
    host = author.host or 'http://127.0.0.1:8000/api/'
    if not host.endswith('/'):
        host = host + '/'
    author_id = host + 'authors/' + str(author.id)
    web = author.web or f"http://127.0.0.1:8000/app/user/{author.id}/"
    try:
        profile_img = author.picture_url or (author.picture.url if author.picture else None)
    except (ValueError, AttributeError):
        profile_img = None
    return {
        "type": "author",
        "id": author_id,
        "host": host,
        "displayName": author.name or author.username,
        "github": author.github or "",
        "profileImage": profile_img,
        "web": web,
    }


@api_view(['GET'])
def api_list_following(request, author_id):
    """
    List all authors that AUTHOR_SERIAL is following
    Local authors only. Simple 'author_id' authentication via query param for testing.
    """
    me = get_object_or_404(Author, id=author_id)

    if str(author_id) != request.GET.get('auth_id', str(author_id)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    following_list = [_author_to_json(a, request) for a in me.following.all()]
    return Response({"following": following_list})

@api_view(['GET', 'PUT', 'DELETE'])
def api_following_detail(request, author_id, foreign_author_fqid):
    """
    GET [local]: check if AUTHOR_SERIAL is following FOREIGN_AUTHOR_FQID
    PUT [local]: generate a follow request for FOREIGN_AUTHOR_FQID
    DELETE [local]: AUTHOR_SERIAL unfollows FOREIGN_AUTHOR_FQID
    """
    me = get_object_or_404(Author, id=author_id)

    if str(author_id) != request.GET.get('auth_id') and str(author_id) != str(request.session.get('author_id')):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    foreign_fqid = unquote(foreign_author_fqid).strip().rstrip("/")
    if foreign_fqid.startswith("http://"):
        foreign_fqid = "https" + foreign_fqid[4:]

    foreign_id, is_local = _extract_local_author_id_from_fqid(foreign_fqid, request)

    if request.method == 'GET':
        if is_local and foreign_id is not None:
            foreign_author = Author.objects.filter(id=foreign_id).first()
            if foreign_author and me.following.filter(id=foreign_author.id).exists():
                return Response(_author_to_json(foreign_author, request))
            return Response({"detail": "Not following"}, status=status.HTTP_404_NOT_FOUND)

        if RemoteFollow.objects.filter(follower=me, followed_fqid=foreign_fqid).exists():
            auth = _credentials_for_remote_author(foreign_fqid)
            if auth:
                try:
                    resp = requests.get(
                        foreign_fqid,
                        headers={"Accept": "application/json"},
                        auth=auth,
                        timeout=10,
                    )
                    if resp.status_code < 400:
                        return Response(resp.json())
                except requests.RequestException:
                    pass
            return Response({"type": "author", "id": foreign_fqid})

        return Response({"detail": "Not following"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        if is_local and foreign_id is not None:
            foreign_author = Author.objects.filter(id=foreign_id).first()
            if not foreign_author or not me.following.filter(id=foreign_author.id).exists():
                return Response({"detail": "Not following"}, status=status.HTTP_404_NOT_FOUND)
            me.following.remove(foreign_author)
            return Response(status=status.HTTP_204_NO_CONTENT)

        deleted, _ = RemoteFollow.objects.filter(
            follower=me,
            followed_fqid=foreign_fqid,
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Not following"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if is_local and foreign_id is not None:
            target = get_object_or_404(Author, id=foreign_id)

            if target == me:
                return Response({"detail": "Cannot follow yourself"}, status=status.HTTP_403_FORBIDDEN)

            if me.following.filter(id=target.id).exists():
                return Response(_author_to_json(target, request), status=status.HTTP_200_OK)

            if not FollowRequest.objects.filter(requester=me, target=target).exists():
                FollowRequest.objects.create(requester=me, target=target)

            return Response({"detail": f"Follow request sent to {target.username}"}, status=status.HTTP_201_CREATED)

        auth = _credentials_for_remote_author(foreign_fqid)
        if not auth:
            return Response(
                {"detail": "No node credentials configured for that remote author"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base = request.build_absolute_uri("/")[:-1]
        author_base = (me.host or "").strip().rstrip("/") or base
        if "/api" not in author_base:
            author_base = f"{author_base.rstrip('/')}/api"
        if author_base.startswith("http://"):
            author_base = "https" + author_base[4:]

        actor_id = f"{author_base}/authors/{me.id}"
        actor_info = {
            "type": "author",
            "id": actor_id,
            "host": author_base,
            "displayName": me.name or me.username,
            "github": me.github or "",
            "profileImage": me.picture_url or "",
            "web": me.web or "",
        }

        payload = {
            "type": "follow",
            "summary": f"{me.name or me.username} wants to follow {foreign_fqid}",
            "actor": actor_info,
            "object": {
                "type": "author",
                "id": foreign_fqid,
            },
        }

        try:
            resp = requests.post(
                f"{foreign_fqid}/inbox",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
                auth=auth,
            )
        except requests.RequestException as e:
            return Response(
                {"detail": f"Could not reach remote inbox: {str(e)[:100]}"},
                status=502,
            )

        RemoteFollow.objects.get_or_create(follower=me, followed_fqid=foreign_fqid)

        if resp.status_code in (200, 201, 202, 204):
            return Response({"detail": "Follow request sent"}, status=status.HTTP_201_CREATED)

        return Response(
            {"detail": f"Inbox rejected ({resp.status_code})"},
            status=resp.status_code,
        )
    
@api_view(['DELETE'])
def api_unfollow_author(request, author_id, foreign_author_id):
    """
    AUTHOR_SERIAL unfollows FOREIGN_AUTHOR_FQID
    Local authors only. Simple 'author_id' authentication via query param for testing.
    """
    me = get_object_or_404(Author, id=author_id)
    target = get_object_or_404(Author, id=foreign_author_id)

    # Manual "authentication" for backend testing
    if str(author_id) != request.GET.get('auth_id', str(author_id)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # Check if following
    if not me.following.filter(id=target.id).exists():
        return Response({"detail": "Not following"}, status=status.HTTP_404_NOT_FOUND)

    me.following.remove(target)
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def api_list_friends(request, author_id):
    """
    List all authors with mutual following (friends).
    Returns JSON with friend id and username.
    """
    author = get_object_or_404(Author, id=author_id)
    friends = author.friends()
    friend_list = [{"id": f.id, "username": f.username} for f in friends]
    return Response({"friends": friend_list})

@api_view(['GET'])
def api_list_follow_requests(request, author_id):
    """
    List all pending follow requests sent to the author.
    Returns JSON with request id, requester id, and username.
    """
    author = get_object_or_404(Author, id=author_id)
    requests = FollowRequest.objects.filter(target=author)
    request_list = [{"id": r.id, "requester_id": r.requester.id, "requester_username": r.requester.username} for r in requests]
    return Response({"follow_requests": request_list})

@api_view(['POST'])
def api_approve_follow(request, req_id):
    """
    Approve a pending follow request.
    Returns JSON confirmation on success.
    """
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.target.followers.add(follow_request.requester)
    follow_request.delete()
    return Response({"detail": "Follow request approved"}, status=status.HTTP_200_OK)


@api_view(['POST'])
def api_deny_follow(request, req_id):
    """
    Deny a pending follow request.
    Returns JSON confirmation on success.
    """
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.delete()
    return Response({"detail": "Follow request denied"}, status=status.HTTP_200_OK)

@api_view(['POST'])
def api_follow_author(request, author_id):
    """
    API endpoint for following a local author.
    Requires query param 'auth_id' for simple auth.
    """
    me = Author.objects.filter(id=request.GET.get('auth_id')).first()
    if not me:
        return Response({"detail": "Invalid auth_id"}, status=status.HTTP_403_FORBIDDEN)

    target = Author.objects.filter(id=author_id).first()
    if not target:
        return Response({"detail": "Target author not found"}, status=status.HTTP_404_NOT_FOUND)

    if target == me:
        return Response({"detail": "Cannot follow yourself"}, status=status.HTTP_403_FORBIDDEN)

    # Already following
    if target in me.following.all():
        return Response({"detail": "Already following"}, status=status.HTTP_409_CONFLICT)

    # Follow request already sent
    if FollowRequest.objects.filter(requester=me, target=target).exists():
        return Response({"detail": "Follow request already sent"}, status=status.HTTP_409_CONFLICT)

    # Create follow request
    FollowRequest.objects.create(requester=me, target=target)
    return Response({"detail": f"Follow request sent to {target.username}"}, status=status.HTTP_201_CREATED)


# --- Followers API (User Story #69 - RESTful interface) ---

@api_view(['GET'])
def api_list_followers(request, author_id):
    """
    GET [local, remote]: List authors who follow AUTHOR_SERIAL.
    URL: /api/authors/{AUTHOR_SERIAL}/followers/
    """
    author = get_object_or_404(Author, id=author_id)
    followers = author.followers.all()
    follower_list = [_author_to_json(a, request) for a in followers]
    return Response({"type": "followers", "followers": follower_list})


def _extract_local_author_id_from_fqid(fqid, request):
    """
    Extract local author id from FQID if this node owns it.
    Returns (id, True) if local, else (None, False).
    """
    try:
        decoded = unquote(fqid)
        # Check if FQID points to our node
        our_base = request.build_absolute_uri('/api/').rstrip('/')
        if our_base[:our_base.index("/api")] not in decoded[:decoded.index("/api")]:
            return decoded, False
        if our_base in decoded or '127.0.0.1' in decoded or 'localhost' in decoded:
            # Extract id: .../authors/123 or .../authors/123/
            parts = decoded.rstrip('/').split('/')
            if 'authors' in parts:
                idx = parts.index('authors')
                if idx + 1 < len(parts):
                    return int(parts[idx + 1]), True
    except (ValueError, IndexError):
        pass
    return None, False


@api_view(['GET', 'PUT', 'DELETE'])
def api_follower_detail(request, author_id, foreign_author_fqid):
    """
    GET [local, remote]: Check if FOREIGN_AUTHOR_FQID is a follower of AUTHOR_SERIAL.
    PUT [local]: Accept follow request (add as follower).
    DELETE [local]: Deny/remove follower.
    URL: /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}/
    """
    author = get_object_or_404(Author, id=author_id)
    foreign_id, is_local = _extract_local_author_id_from_fqid(foreign_author_fqid, request)

    if not is_local or foreign_id is None:
        if request.method == 'GET' and RemoteFollower.objects.filter(actor_fqid=foreign_id, target = author_id).exists():
            return Response(status=200)
        return Response({"detail": "Foreign author not found on this node"}, status=404)
    
    try:
        foreign_author = Author.objects.get(id=foreign_id)
    except Author.DoesNotExist:
        return Response({"detail": "Author not found"}, status=404)

    if request.method == 'GET':
        if author.followers.filter(id=foreign_author.id).exists():
            return Response(_author_to_json(foreign_author, request))
        return Response({"detail": "Not a follower"}, status=404)

    # PUT and DELETE require auth
    if str(author_id) != request.GET.get('auth_id') and str(author_id) != str(request.session.get('author_id')):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        # Accept follow request: add foreign_author to author's followers
        follow_req = FollowRequest.objects.filter(requester=foreign_author, target=author).first()
        if not follow_req:
            return Response({"detail": "No matching follow request"}, status=404)
        author.followers.add(foreign_author)
        follow_req.delete()
        return Response(_author_to_json(foreign_author, request))

    if request.method == 'DELETE':
        # Deny/remove: remove from followers, delete any pending request
        FollowRequest.objects.filter(requester=foreign_author, target=author).delete()
        if author.followers.filter(id=foreign_author.id).exists():
            author.followers.remove(foreign_author)
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(status=405)

@api_view(['GET', 'PUT'])
def api_edit_profile(request, author_id):
    """
    Get or update author profile.
    """
    me = get_object_or_404(Author, id=author_id)

    # Simple auth check
    if str(author_id) != request.GET.get('auth_id', str(author_id)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        data = {
            "username": me.username,
            "name": me.name,
            "description": me.description,
            "github": me.github,
            "picture": me.picture.url if me.picture else None
        }
        return Response(data)

    if request.method == 'PUT':
        name = request.data.get('name')
        description = request.data.get('description')
        github = request.data.get('github')
        picture_url = request.data.get('picture')  

        if name is not None:
            me.name = name
        if description is not None:
            me.description = description
        if github is not None:
            me.github = github
        if picture_url:
            me.picture = picture_url  # store the URL directly in your ImageField/TextField

        me.save()
        return Response({"detail": "Profile updated successfully"}, status=status.HTTP_200_OK)