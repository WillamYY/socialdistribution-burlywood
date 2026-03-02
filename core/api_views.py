from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.models import Author, FollowRequest

@api_view(['GET'])
def api_list_following(request, author_id):
    """
    List all authors that AUTHOR_SERIAL is following
    Local authors only. Simple 'author_id' authentication via query param for testing.
    """
    me = get_object_or_404(Author, id=author_id)

    if str(author_id) != request.GET.get('auth_id', str(author_id)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    following_list = [
        {
    "type": "author",
    "id": f"http://127.0.0.1:8000/api/authors/{a.id}",
    "host": "http://127.0.0.1:8000/api/",
    "displayName": a.name or a.username,
    "github": a.github,
    "profileImage": a.picture.url if a.picture else None,
    "web": f"http://127.0.0.1:8000/authors/{a.id}",
}
        for a in me.following.all()
    ]
    return Response({"following": following_list})

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
        picture = request.FILES.get('picture')

        if name is not None:
            me.name = name
        if description is not None:
            me.description = description
        if github is not None:
            me.github = github
        if picture:
            me.picture = picture

        me.save()
        return Response({"detail": "Profile updated successfully"}, status=status.HTTP_200_OK)