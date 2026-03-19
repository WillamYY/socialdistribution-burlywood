# Create your views here.
import base64
from email.mime import base
import uuid
import requests
from urllib.parse import unquote
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Author, AuthorRequest, FollowRequest
from entries.models import Entry
from interactions.models import Like, Comment
from .serializers import LikesSerializer, LikeSerializer, EntrySerializer, EntriesSerializer, CommentSerializer

# Create your views here.
def check_visibility(entry, viewer_id, is_list=False):
    """
    Helper function to verify if a user can see an entry.
    """
    # Not found if entry is DELETED
    if entry.visibility == "DELETED":
        return False
    # Anyone with the link can see Public and Unlisted
    if entry.visibility == "PUBLIC":
        return True
    if entry.visibility == "UNLISTED":
        if not is_list:
            # Direct link access
            return True
        else:
            # If from list, only the author or a follower can see it in a feed
            if not viewer_id:
                return False
            if str(entry.author.id) == str(viewer_id):
                return True
            if entry.author.followers.filter(id=viewer_id).exists():
                return True
            return False

    # If not logged in, cannot see anything else
    if not viewer_id:
        return False
        
    # Author can always see their own non-deleted stuff
    if str(entry.author.id) == str(viewer_id):
        return True
        
    # Friends check for mutual followers
    if entry.visibility == "FRIENDS":
        try:
            viewer = Author.objects.get(id=viewer_id)
            entry_author = Author.objects.get(id=entry.author.id)
            # Check if the viewer is in entry author's friends list
            return viewer in entry_author.friends()
        except Author.DoesNotExist:
            return False
            
    return False

def is_remote_fqid(fqid, request):
    """
    Helper function to check if a given FQID belongs to a remote node.
    """
    current_host = request.get_host()
    return current_host not in fqid and fqid.startswith("http")

def fetch_remote_json(remote_url):
    """
    Helper function to safely fetch JSON from a remote node.
    """
    try:
        # Specify to accept JSON only
        response = requests.get(remote_url, headers={'Accept': 'application/json'}, timeout=5)
        if response.status_code == 200:
            # Fetched the JSON object successfully
            return Response(response.json(), status=200)
        elif response.status_code == 404:
            # Remote resource not found
            return Response({"detail": "Remote resource not found."}, status=404)
        else:
            return Response({"detail": f"Remote node error: {response.status_code}"}, status=response.status_code)
    except requests.exceptions.RequestException as e:
        return Response({"detail": f"Error connecting to remote node: {str(e)}"}, status=502)

def fetch_remote_image(remote_url):
    """
    Helper function to safely fetch binary image data from a remote node.
    """
    try:
        response = requests.get(remote_url, timeout=5)    
        if response.status_code == 200:
            # Fetch the type of file
            content_type = response.headers.get('Content-Type', '').lower()
            # Check if image 
            if content_type.startswith('image/'):
                # Pass the binary data and the exact format back to the browser
                return HttpResponse(response.content, content_type=content_type)
            else:
                # Image not found
                return HttpResponse("Remote node did not return valid image data.", status=404)         
        elif response.status_code == 404:
            return HttpResponse("Remote image not found.", status=404)
        else:
            return HttpResponseForbidden(f"Remote node error: {response.status_code}", status=response.status_code)
    except requests.exceptions.RequestException as e:
        return HttpResponse(f"Error connecting to remote node: {str(e)}", status=502)

@api_view(['GET'])
def ApiAuthors(request):
    query_string = request.META["QUERY_STRING"].split("&")
    page = 1
    size = None
    for query in query_string:
        # Gets the page number from query string
        if query.split("=")[0] == "page":
            if query.split("=")[1].isdigit():
                page = int(query.split("=")[1])
        # Gets the size  from query string
        if query.split("=")[0] == "size":
            if query.split("=")[1].isdigit():
                size = int(query.split("=")[1])
    # gets all the authors
    allAuthors = Author.objects.all()
    data = {"type":"authors"} 
    authors = []
    # Gets the relevant information from each author
    for author in allAuthors:
        # Gets the authors info
        authorID = author.host + "/authors/" + str(author.id)
        authorInfo = {"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web}
        authors.append(authorInfo)
    # If size is not specified returns all authors
    if size == None:
        data["authors"] = authors
    else:
        if page  * size < len(authors):
            # For case when we can make a full page of that size
            if (page + 1) * size < len(authors):
                data["authors"] = authors[page * size:(page + 1) * size]
            # Case where the page is not complete because it encounters the end of the list
            else:
                data["authors"] = authors[page * size:]
        # Returns empty if page and size are out of range
        else:
            data["authors"] = []
    return Response(data)

# Single author API endpoint
@api_view(['GET','PUT'])
def HandleApiAuthor(request, id):
    return ApiAuthor(request, id)

def ApiAuthor(request,id):
    if request.method == "GET":
        author = get_object_or_404(Author,pk=id) # Gets the author
        authorID = author.host + "/authors/" + str(author.id)
        # Creates the information that will be returned
        authorInfo = {"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web}
        return Response(authorInfo)
    elif request.method == "PUT":
        # Replaces the object if it is put on top of
        if not Author.objects.filter(id = id).exists():
            # Ensures that the authors id matches the correct Id of where it is being placed and that the name is unique
            if str(id) == request.data.get("id").split("/")[-1] and not Author.objects.filter(username = request.data.get("displayName")).exists():
                # Creates an author request with the information
                author = AuthorRequest(id = id,username = request.data.get("displayName"),name = request.data.get("displayName"),github = request.data.get("github"),web = request.data.get("web"), host = request.data.get("host"),picture_url = request.data.get("profileImage"))
                author.save()
                authorID = author.host + "/authors/" + str(author.id)
                return Response({"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web},status = 201)
            # If the authors Id is invalid return a 400 respose
            else:
                return Response(status = 400)
        # If the user does exist replace it's info with the new info
        else:
            # Ensures that the authors id matches the correct Id of where it is being placed
            if str(id) == request.data.get("id").split("/")[-1]:
                # If an author already exists with the name that is not the current author return a error code of 400
                if Author.objects.filter(username = request.data.get("displayName")).exists():
                    if get_object_or_404(Author,name=request.data.get("displayName")).id != id:
                        return Response(status = 400)
                author = get_object_or_404(Author,pk=id) # Gets the author
                # Updates the authors info
                author.id = id
                author.host = request.data.get("host")
                author.username = request.data.get("displayName")
                author.name = request.data.get("displayName")
                author.github = request.data.get("github")
                author.web = request.data.get("web")
                author.picture_url = request.data.get("profileImage")
                author.save()
                # Turns the authors id into it's string
                authorID = author.host + "/authors/" + str(author.id)
                return Response({"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web})
            else:
                return Response(status = 400)
    # Returns a 405 error if using invalid method
    else:
        return Response(status = 405)

# Returns who liked a specific entry with author described
@api_view(["GET"])
def ApiAuthorAndEntryLikes(request,author_id,entry_id):
    # Ensures the entry exists before accessing it
    if request.GET.get("page_number") and request.GET.get("page_number").isnumeric():
        if int(request.GET.get("page_number")) > 0:
            page_number = int(request.GET.get("page_number"))
        else:
            page_number = 1
    else:
        page_number = 1
    if request.GET.get("size") and request.GET.get("size").isnumeric():
        if int(request.GET.get("size")) > 0:
            size = int(request.GET.get("size"))
        else:
            size = 5
    else:
        size = 5

    if Entry.objects.filter(id = entry_id).exists():
        entry = Entry.objects.get(id = entry_id)
    else:
        return Response(status = 404)

    # Check the visibility for the logged-in user
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return Response({"detail": "Forbidden"}, status=403)
    
    # getting the URL of the object requested
    liked_obj = request.build_absolute_uri(f"/api/authors/{author_id}/entries/{entry.id}/")

    # getting all the likes whose object is the given liked object, ordered by publish date
    likes = Like.objects.filter(object__contains=str(entry_id)).order_by("-published", "-id")

    count = likes.count()
    # should only get 5 likes per entry
    start = (page_number - 1) * size
    end = start + size
    src = likes[start:end]

    # Finds the link to the object that was liked
    entryURL = request.build_absolute_uri()
    # Serializes the data
    likesSerializer = LikesSerializer({"page_number":page_number,"size":size,"count":count,"src":src},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
    return Response(likesSerializer.data)

# Returns who liked a specific entry with no author
@api_view(["GET"])
def ApiEntryLikes(request, entry_fqid):
    # Ensures the entry exists before accessing it
    # From https://stackoverflow.com/questions/150505/how-to-get-get-request-values-in-django by camlfan, downloaded 2026-03-01
    if request.GET.get("page_number") and request.GET.get("page_number").isnumeric():
        if int(request.GET.get("page_number")) > 0:
            page_number = int(request.GET.get("page_number"))
        else:
            page_number = 1
    else:
        page_number = 1
    if request.GET.get("size") and request.GET.get("size").isnumeric():
        if int(request.GET.get("size")) > 0:
            size = int(request.GET.get("size"))
        else:
            size = 5
    else:
        size = 5
    entry_id = entry_fqid.split("/")[-1]
    if Entry.objects.filter(id = entry_id).exists():
        entry = Entry.objects.get(id = entry_id)
    else:
        return Response(status = 404)

    # Check the visibility for the logged-in user
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return Response({"detail": "Forbidden"}, status=403)
    
    # getting local authors only, order by publish date
    likes = Like.objects.filter(object__contains=str(entry_id)).order_by("-published", "-id")

    count = likes.count()
    # should only get 5 likes per entry
    start = (page_number - 1) * size
    end = start + size
    src = likes[start:end]

    # Finds the link to the object that was liked
    entryURL = request.build_absolute_uri()
    # Serializes the data
    likesSerializer = LikesSerializer({"page_number":page_number,"size":size,"count":count,"src":src},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
    return Response(likesSerializer.data)

# Unified Inbox (User Story #69): routes by object type
@api_view(["POST"])
def ApiInbox(request, author_id):
    """
    POST [remote]: Unified inbox accepts like, follow, comment, entry.
    Routes to appropriate handler by request body type.
    """
    obj_type = (request.data.get("type") or "like").lower()
    if obj_type == "follow":
        return _inbox_handle_follow(request, author_id)
    if obj_type == "comment":
        return _inbox_handle_comment(request, author_id)
    if obj_type == "entry":
        return _inbox_handle_entry(request, author_id)
    return _inbox_handle_like(request, author_id)


def _inbox_handle_follow(request, author_id):
    """Handle follow request: actor wants to follow object (our author)."""
    target = get_object_or_404(Author, id=author_id)
    actor_data = request.data.get("actor") or {}
    actor_id_str = (actor_data.get("id") or "").strip().rstrip("/")
    if not actor_id_str:
        return Response({"detail": "Missing actor"}, status=400)
    # For local actor: extract id and get Author
    try:
        actor_local_id = int(actor_id_str.split("/")[-1])
        actor = Author.objects.filter(id=actor_local_id).first()
    except (ValueError, IndexError):
        actor = None
    if not actor:
        return Response({"detail": "Actor author not found on this node"}, status=404)
    if actor.id == author_id:
        return Response({"detail": "Author cannot follow themselves"}, status=400)
    if FollowRequest.objects.filter(requester=actor, target=target).exists():
        return Response({"detail": "Follow request already sent"}, status=409)
    if actor.following.filter(id=target.id).exists():
        return Response({"detail": "Already following"}, status=409)
    FollowRequest.objects.create(requester=actor, target=target)
    return Response({"detail": "Follow request received"}, status=202)


def _inbox_handle_comment(request, author_id):
    """Handle comment: add comment to an entry."""
    target_author = get_object_or_404(Author, id=author_id)
    entry_url = request.data.get("entry") or (request.data.get("object") if isinstance(request.data.get("object"), str) else None)
    if not entry_url:
        return Response({"detail": "Missing entry"}, status=400)
    entry_uuid = entry_url.rstrip("/").split("/")[-1]
    try:
        entry = Entry.objects.get(id=entry_uuid, author=target_author)
    except Entry.DoesNotExist:
        return Response({"detail": "Entry not found"}, status=404)
    if entry.visibility == "DELETED":
        return Response({"detail": "Entry not found"}, status=404)
    author_data = request.data.get("author") or {}
    author_url = author_data.get("id") or ""
    comment_text = request.data.get("comment") or ""
    if not comment_text or not author_url:
        return Response({"detail": "Missing author or comment"}, status=400)
    base = request.build_absolute_uri("/")[:-1]
    entry_fqid = f"{base}/api/authors/{author_id}/entries/{entry.id}"
    Comment.objects.create(
        id=f"{base}/comments/{uuid.uuid4()}",
        author=author_url,
        entry=entry_fqid,
        comment=comment_text,
        contentType=request.data.get("contentType", "text/plain"),
    )
    return Response({"detail": "Comment received"}, status=202)


def _inbox_handle_entry(request, author_id):
    """Handle incoming entry: store for stream (basic support)."""
    return Response({"detail": "Entry received (inbox storage not yet implemented)"}, status=202)


def _inbox_handle_like(request, author_id):
    """Handle like: existing like logic."""
    obj_url = request.data.get("object")
    if not obj_url:
        return Response({"detail": "Missing object"}, status=400)
    obj_url = obj_url.rstrip("/")
    entry_id = obj_url.split("/")[-1]
    try:
        entry = Entry.objects.get(id=entry_id)
    except (Entry.DoesNotExist, ValueError):
        return Response(status=404)
    if entry.visibility == "DELETED":
        return Response(status=404)
    if entry.author.id != author_id:
        return Response(status=400)
    author_data = request.data.get("author") or {}
    author_url = (author_data.get("id") if isinstance(author_data, dict) else None) or ""
    if not author_url:
        return Response(status=400)
    if Like.objects.filter(author=author_url, object=obj_url.rstrip("/")).exists():
        return Response(status=409)
    like = Like(
        author=author_url,
        object=obj_url.rstrip("/"),
        id=f"{request.build_absolute_uri('/')[:-1]}/likes/{uuid.uuid4()}",
        uuid=uuid.uuid4(),
    )
    like.save()
    return Response(LikeSerializer(like).data, status=201)


        
@api_view(["GET"])
def ApiAuthorLiked(request, author_id):
    if request.GET.get("page_number") and request.GET.get("page_number").isnumeric():
        if int(request.GET.get("page_number")) > 0:
            page_number = int(request.GET.get("page_number"))
        else:
            page_number = 1
    else:
        page_number = 1
    if request.GET.get("size") and request.GET.get("size").isnumeric():
        if int(request.GET.get("size")) > 0:
            size = int(request.GET.get("size"))
        else:
            size = 5
    else:
        size = 5
    author_fqid = "/".join(request.build_absolute_uri().split("/")[:-1])

    likes_tmp = Like.objects.filter(author = author_fqid).order_by("-published", "id")
    logged_in_id = request.session.get("author_id")
    # only deal with local for now
    likes = []
    for like in likes_tmp:
        entry_id = like.object.rstrip("/").split("/")[-1]
        entry = Entry.objects.filter(id=entry_id).first()
        # Check the visibility for the logged-in user
        if entry and check_visibility(entry, logged_in_id):
            likes.append(like)

    count = len(likes)
    # should only get 5 likes per entry
    start = (page_number - 1) * size
    end = start + size
    src = likes[start:end]

    # Finds the link to the object that was liked
    entryURL = request.build_absolute_uri()
    # Serializes the data
    likesSerializer = LikesSerializer({"page_number":page_number,"size":size,"count":count,"src":src},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
    return Response(likesSerializer.data)

@api_view(["GET"])
def ApiSingleLikeRemoteLocal(request, author_id, like_id):
    author_fqid = "/".join(request.build_absolute_uri().split("/")[:-2])
    if Like.objects.filter(uuid = like_id, author = author_fqid).exists():
        like = Like.objects.get(uuid = like_id, author = author_fqid)
        like_json = LikeSerializer(like)
        return Response(like_json.data)
    return Response(status = 404)

@api_view(["GET"])
def ApiAuthorLikedLocal(request, author_fqid):
    if request.GET.get("page_number") and request.GET.get("page_number").isnumeric():
        if int(request.GET.get("page_number")) > 0:
            page_number = int(request.GET.get("page_number"))
        else:
            page_number = 1
    else:
        page_number = 1
    if request.GET.get("size") and request.GET.get("size").isnumeric():
        if int(request.GET.get("size")) > 0:
            size = int(request.GET.get("size"))
        else:
            size = 5
    else:
        size = 5

    likes_tmp = Like.objects.filter(author = author_fqid).order_by("-published", "id")
    logged_in_id = request.session.get("author_id")
    likes = []
    for like in likes_tmp:
        entry_id = like.object.rstrip("/").split("/")[-1]
        entry = Entry.objects.filter(id=entry_id).first()
        # Check the visibility for the logged-in user
        if entry and check_visibility(entry, logged_in_id):
            likes.append(like)

    count = len(likes)
    # should only get 5 likes per entry
    start = (page_number - 1) * size
    end = start + size
    src = likes[start:end]

    # Finds the link to the object that was liked
    entryURL = request.build_absolute_uri()
    # Serializes the data
    likesSerializer = LikesSerializer({"page_number":page_number,"size":size,"count":count,"src":src},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
    return Response(likesSerializer.data)

@api_view(["GET"])
def ApiSingleLikeLocal(request, like_url):
    like_id = like_url.split("/")[-1]
    #author_fqid = "/".join(like_url.split("/")[:6])
    if Like.objects.filter(uuid = like_id):
        like_object = Like.objects.get(uuid = like_id)

        like_json = LikeSerializer(like_object)
        return Response(like_json.data)
    else:
        return Response(status = 404)

# Returns a paginated list of entries for a specific author
@api_view(['GET', 'POST'])
def ApiEntries(request, author_id):
    """
    URL ://service/api/authors/{AUTHOR_SERIAL}/entries/
    """
    # Ensure the author exists before trying to fetch their entries
    author = get_object_or_404(Author, pk=author_id)
    
    if request.method == 'GET':
        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 5))
        logged_in_id = request.session.get("author_id")
        
        # Fetch all non-deleted entries
        all_entries = Entry.objects.filter(author=author).exclude(visibility="DELETED").order_by('-published')
        
        # Query the entries by checking visibility for logged-in user
        visible_entries = [e for e in all_entries if check_visibility(e, logged_in_id, is_list=True)]
        
        # Paginate the queryset
        start = (page - 1) * size
        end = start + size
        paginated_entries = visible_entries[start:end]
        
        # Package the data for EntriesSerializer
        data = {
            "page_number": page,
            "size": size,
            "count": len(visible_entries),
            "src": paginated_entries
        }
        
        # Serialize and return
        serializer = EntriesSerializer(data, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Ensure the logged in user is the author
        if str(request.session.get("author_id")) != str(author_id):
            return Response({"detail": "Forbidden: You cannot post as another author."}, status=403)

        # Ensure the visibility is set properly
        allowed_visibility = {"PUBLIC", "FRIENDS", "UNLISTED", "DELETED"}
        visibility = request.data.get("visibility", "PUBLIC")
        if visibility not in allowed_visibility:
            return Response({"detail": "Invalid visibility."}, status=400)

        # Create a new entry from the incoming JSON object
        new_entry = Entry.objects.create(
            author=author,
            title=request.data.get("title", ""),
            description=request.data.get("description", ""),
            contentType=request.data.get("contentType", "text/plain"),
            content=request.data.get("content", ""),
            visibility=request.data.get("visibility", "PUBLIC")
        )
        
        # Return the newly created entry using your teammate's serializer
        serializer = EntrySerializer(new_entry, context={'request': request})
        return Response(serializer.data, status=201)

# Returns a single specific entry
@api_view(['GET', 'PUT', 'DELETE'])
def ApiEntry(request, author_id, entry_id):
    """
    URL: ://service/api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    """
    # Try to get the entry first
    # None if not found; avoid 404 immediately due to PUT-create behavior
    entry = Entry.objects.filter(pk=entry_id, author_id=author_id).first()

    if request.method == 'GET':
        # Cannot access deleted entries through the API
        if not entry or entry.visibility == "DELETED":
            return Response({"detail": "Not found."}, status=404)

        # Check the visibility for the logged-in user
        logged_in_id = request.session.get("author_id")
        if not check_visibility(entry, logged_in_id):
            return Response({"detail": "Forbidden"}, status=403)
        
        # Serialize and return
        serializer = EntrySerializer(entry, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Retrieve the logged-in author's ID from the session
        session_author_id = request.session.get("author_id")

        # Ensure only the author can edit the entry
        if str(session_author_id) != str(author_id):
            return Response(
                {"detail": "You do not have permission to modify this entry."}, 
                status=403
            )
        
        # Ensure the visibility is set properly
        allowed_visibility = {"PUBLIC", "FRIENDS", "UNLISTED", "DELETED"}
        visibility = request.data.get("visibility", "PUBLIC")
        if visibility not in allowed_visibility:
            return Response({"detail": "Invalid visibility."}, status=400)
        
        author = get_object_or_404(Author, pk=author_id)
        # If entry DNE, create it with the provided entry id
        if not entry:
            entry = Entry(id=entry_id, author=author)
        
        # Update the entry with new data
        entry.title = request.data.get("title", entry.title)
        entry.description = request.data.get("description", entry.description)
        entry.contentType = request.data.get("contentType", entry.contentType)
        entry.content = request.data.get("content", entry.content)
        entry.visibility = request.data.get("visibility", entry.visibility)
        entry.save()
        
        # Serialize and return
        serializer = EntrySerializer(entry, context={'request': request})
        return Response(serializer.data, status=200)
    
    elif request.method == 'DELETE':
        # Ensure a non-deleted entry first
        if not entry:
            return Response({"detail": "Not found."}, status=404)

        # Security check for deletion
        if str(request.session.get("author_id")) != str(author_id):
            return Response({"detail": "Forbidden"}, status=403)

        # Soft delete by changing visibility to DELETED
        entry.visibility = "DELETED"
        entry.save()
        
        return Response(status=204)

@api_view(['GET'])
def ApiEntryGlobal(request, entry_fqid):
    """
    Global entry endpoint with entry FQID.
    URL: /api/entries/<path:entry_fqid>/
    """
    # Clean up the trailing slash
    entry_fqid = entry_fqid.rstrip('/')

    # Proxy if remote
    if is_remote_fqid(entry_fqid, request):
        return fetch_remote_json(entry_fqid)

    # Handle if local
    try:
        entry_id = entry_fqid.split('/')[-1]
        entry = Entry.objects.get(id=entry_id)
    except (Entry.DoesNotExist, ValueError):
        return Response({"detail": "Not found."}, status=404)

    # Check visibility
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
            return Response({"detail": "Forbidden"}, status=403)

    # Serialize and return
    serializer = EntrySerializer(entry, context={'request': request})
    return Response(serializer.data, status=200)
    


def _parse_entry_fqid(entry_fqid, request):
    """Parse entry FQID to get (author_id, entry_id) for local entries."""
    try:
        decoded = unquote(entry_fqid)
        parts = decoded.rstrip("/").split("/")
        if "entries" in parts:
            idx = parts.index("entries")
            if idx + 1 < len(parts):
                entry_id = parts[idx + 1]
                if "authors" in parts:
                    aidx = parts.index("authors")
                    if aidx + 1 < len(parts):
                        author_id = int(parts[aidx + 1])
                        return author_id, entry_id
    except (ValueError, IndexError):
        pass
    return None, None


def _parse_author_fqid(author_fqid):
    """Parse author FQID to get local author id."""
    try:
        decoded = unquote(author_fqid)
        parts = decoded.rstrip("/").split("/")
        if "authors" in parts:
            idx = parts.index("authors")
            if idx + 1 < len(parts):
                return int(parts[idx + 1])
    except (ValueError, IndexError):
        pass
    return None


@api_view(['GET'])
def ApiEntryByFqid(request, entry_fqid):
    """GET [local]: Retrieve entry by FQID. URL: /api/entries/{ENTRY_FQID}"""
    author_id, entry_id = _parse_entry_fqid(entry_fqid, request)
    if author_id is None:
        return Response({"detail": "Not found"}, status=404)
    return ApiEntry(request, author_id, entry_id)


@api_view(['GET'])
def ApiAuthorByFqid(request, author_fqid):
    """GET [remote]: Retrieve author by FQID. URL: /api/authors/{AUTHOR_FQID}"""
    author_id = _parse_author_fqid(author_fqid)
    if author_id is None:
        return Response({"detail": "Not found"}, status=404)
    return ApiAuthor(request, author_id)

@api_view(['GET'])
def ApiEntryImage(request, author_id=None, entry_id=None, entry_fqid=None):
    """
    Returns the raw image data for an entry.
    Allows Markdown to link to images.
    URL: ://service/api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image
    URL: ://service/api/entries/{ENTRY_FQID}/image
    """
    # Proxy if remote
    if entry_fqid is not None:
        entry_fqid = entry_fqid.rstrip("/")

        # If a remote URL, proxy the request to the other node
        if is_remote_fqid(entry_fqid, request):
            # Fetch from remote node's image endpoint
            remote_image_url = f"{entry_fqid}/image"
            return fetch_remote_image(remote_image_url)
        
        # If a local URL, simply extract the entry ID
        entry_id = entry_fqid.split("/")[-1]

    # Handle if local
    if author_id is not None:
        entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)
    else:
        entry = get_object_or_404(Entry, id=entry_id)

    # Check if base64 data, implying an image
    if ";base64" not in entry.contentType:
        return HttpResponse("This entry is not an image.", status=404)
    
    # Not found if entry is DELETED
    if entry.visibility == "DELETED":
        return HttpResponse(status=404)
    
    # Check the visibility for the logged-in user
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return HttpResponseForbidden("You do not have permission to view this image.")
    
    # Decode and Serve
    try:
        # Strip the content string to get the actual base64 data 
        content_str = entry.content
        if "," in content_str:  # i.e. data:image/png;base64,... prefix
            content_str = content_str.split(",")[1]
        
        # Decode image into raw binary data
        image_binary = base64.b64decode(content_str.strip())
        
        # Extract the actual base64 string and the MIME type
        # MIME == Multipurpose Internet Mail Extension: type of data being transmitted over internet 
        mime_type = entry.contentType.split(';')[0]     # i.e. format like "image/png;base64"

        # Return raw binary data with the correct MIME type
        return HttpResponse(image_binary, content_type=mime_type)
    except Exception as e:
        # Failed to decode base64; internal server error
        return HttpResponse(f"Failed to decode image: {str(e)}", status=500)
    
@api_view(["GET"])
def HandleApiEntryComments(request, author_id, entry_id):
    return ApiEntryComments(request, author_id, entry_id)

def ApiEntryComments(request, author_id, entry_id):
    """
    Returns comments for an entry
    GET /api/authors/{author_id}/entries/{entry_id}/comments
    """
    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return Response(status=403)

    api_entry_fqid = request.build_absolute_uri(
        f"/api/authors/{author_id}/entries/{entry_id}/"
    )
    app_entry_fqid = request.build_absolute_uri(
        f"/app/entry/{entry_id}/"
    )

    comments = Comment.objects.filter(entry__in=[api_entry_fqid, app_entry_fqid]).order_by("-published", "-id")

    serializer = CommentSerializer(comments, many=True)

    return Response({
        "type": "comments",
        "id": request.build_absolute_uri(),
        "page_number": 1,
        "size": comments.count(),
        "count": comments.count(),
        "src": serializer.data
    })


@api_view(['GET'])
def ApiEntryCommentsByFqid(request, entry_fqid):
    """GET [local, remote]: Comments on entry by FQID. URL: /api/entries/{ENTRY_FQID}/comments/"""
    author_id, entry_id = _parse_entry_fqid(entry_fqid, request)
    if author_id is None:
        return Response({"detail": "Not found"}, status=404)
    return ApiEntryComments(request, author_id, entry_id)


@api_view(['GET'])
def ApiCommentLikes(request, author_id, entry_id, comment_fqid):
    """GET [local, remote]: Likes on a comment. URL: .../comments/{COMMENT_FQID}/likes"""
    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return Response({"detail": "Forbidden"}, status=403)
    comment_id = unquote(comment_fqid)
    page_number = max(1, int(request.GET.get("page_number", 1))) if request.GET.get("page_number", "1").isdigit() else 1
    size = max(1, int(request.GET.get("size", 5))) if request.GET.get("size", "5").isdigit() else 5
    likes = Like.objects.filter(object=comment_id).order_by("-published")
    count = likes.count()
    start = (page_number - 1) * size
    src = likes[start : start + size]
    link = request.build_absolute_uri()
    obj_url = comment_id if not link.endswith("/likes") else link[:-5].rstrip("/")
    likes_data = LikesSerializer(
        {"page_number": page_number, "size": size, "count": count, "src": src},
        context={"link": link, "object": obj_url}
    )
    return Response(likes_data.data)


@api_view(["POST"])
def ApiAddComment(request, author_id, entry_id):
    """
    Create a comment on an entry
    POST /api/authors/{author_id}/entries/{entry_id}/comments/
    """

    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    # Check the visibility for the logged-in user
    logged_in_id = request.session.get("author_id")
    if not check_visibility(entry, logged_in_id):
        return Response({"detail": "Forbidden from commenting on this entry."}, status=403)

    author_url = request.build_absolute_uri(f"/api/authors/{logged_in_id}/")
    comment_text = request.data.get("comment")

    entry_fqid = request.build_absolute_uri(
        f"/api/authors/{author_id}/entries/{entry_id}/"
    )

    base = request.build_absolute_uri('/')[:-1]

    new_comment = Comment.objects.create(
        id=f"{base}/comments/{uuid.uuid4()}",
        author=author_url,
        entry=entry_fqid,
        comment=comment_text,
        contentType=request.data.get("contentType", "text/plain"),
    )

    serializer = CommentSerializer(new_comment)

    return Response(serializer.data, status=201)

@api_view(['GET'])
# TODO: Currently, this API returns only local public entries.
# Once the inbox feature is implemented in the next phase, this API should merge those entries into the response
def ApiBrowsePublicEntries(request):
    """
    Browse all public entries (local only for now)
    GET /api/entries/public/?page=<page>&size=<size>
    """
    # Pagination parameters
    page = int(request.query_params.get('page', 1))
    size = int(request.query_params.get('size', 5))
    
    # Logged-in user
    logged_in_id = request.session.get("author_id")
    
    # Fetch all local public entries (exclude deleted)
    public_entries = Entry.objects.filter(visibility="PUBLIC").exclude(visibility="DELETED").order_by('-published')
    
    # filter by visibility logic if needed (for friends/followers)
    visible_entries = [e for e in public_entries if check_visibility(e, logged_in_id)]
    
    # Pagination
    start = (page - 1) * size
    end = start + size
    paginated_entries = visible_entries[start:end]
    
    # Build response
    data = {
        "page_number": page,
        "size": size,
        "count": len(visible_entries),
        "src": paginated_entries
    }
    
    serializer = EntriesSerializer(data, context={'request': request})
    return Response(serializer.data)