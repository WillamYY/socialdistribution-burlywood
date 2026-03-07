# Create your views here.
import base64
import uuid
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render,get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Author, AuthorRequest
from entries.models import Entry
from interactions.models import Like, Comment
from .serializers import LikesSerializer, LikeSerializer, EntrySerializer, EntriesSerializer, CommentSerializer

# Create your views here.
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
        authorID = author.host + "authors/" + str(author.id)
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
def ApiAuthor(request,id):
    if request.method == "GET":
        author = get_object_or_404(Author,pk=id) # Gets the author
        authorID = author.host + "authors/" + str(author.id)
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
                authorID = author.host + "authors/" + str(author.id)
                return Response({"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture_url,"web":author.web})
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
                authorID = author.host + "authors/" + str(author.id)
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
    # Only getting entries that are PUBLIC or UNLISTED
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

    if Entry.objects.filter(id = entry_id, visibility__in = ["PUBLIC", "UNLISTED"]).exists():
        # getting the URL of the object requested
        liked_obj = "/".join(request.build_absolute_uri().split("/")[:-1])

        # getting all the likes whose object is the given liked object, ordered by publish date
        likes = Like.objects.filter(object = liked_obj).order_by("-published")

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
    else:
        # Returns 404 if the entry does not exist
        return Response(status = 404)

# Returns who liked a specific entry with no author
@api_view(["GET"])
def ApiEntryLikes(request, entry_fqid):
    # Ensures the entry exists before accessing it
    # Only getting entries that are PUBLIC or UNLISTED
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
    if Entry.objects.filter(id = entry_id, visibility__in = ["PUBLIC", "UNLISTED"]).exists():
        # getting local authors only, order by publish date
        likes = Like.objects.filter(object = entry_fqid).order_by("-published")

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
    else:
        # Returns 404 if the entry does not exist
        return Response(status = 404)

# Sends a like to the author (Currently creates a like on an entry only)
@api_view(["POST"])
def ApiSendLike(request,author_id):
    # Gets the id of the liked entry from the url
    entry_id = request.data.get("object").split("/")[-1]
    # Ensures the entry exists before accessing it
    if Entry.objects.filter(id = entry_id).exists():
        entry = Entry.objects.get(id = entry_id)
        # If the entry is from a different author show an error code
        if entry.author.id != author_id:
            return Response(status = 400)
        else:
            # Gets the id of the author from data
            likeAuthor = request.data.get("author").get("id").split("/")[-1]
            # If the author doing the liking does not exist return an error
            if not Author.objects.filter(id = likeAuthor).exists():
                return Response(status = 400)
            likeAuthor = Author.objects.get(id = likeAuthor)

            if Like.objects.filter(author = request.data.get("author").get("id"), object = request.data.get("object")).exists():
                return Response(status = 409)

            like = Like(author = request.data.get("author").get("id"), object = request.data.get("object"))

            like.save()
            like_serializer = LikeSerializer(like)
            return Response(status = 201, data = like_serializer.data)
    else:
        return Response(status = 404)
    
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

    likes_tmp = Like.objects.filter(author = author_fqid).order_by("-published")
    # the liked object's visibilities must either be PUBLIC or UNLISTED
    # only deal with local for now
    likes = []
    for like in likes_tmp:
        entry_id = like.object.split("/")[-1]
        if Entry.objects.filter(id = entry_id, visibility__in = ["PUBLIC", "UNLISTED"]).exists():
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
    likeURL = f"{request.build_absolute_uri('/')[:-1]}/likes/{uuid.uuid4()}"
    if Like.objects.filter(id = likeURL, author = author_fqid).exists():
        like = Like.objects.get(id = likeURL, author = author_fqid)
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

    likes_tmp = Like.objects.filter(author = author_fqid).order_by("-published")
    likes = []
    for like in likes_tmp:
        entry_id = like.object.split("/")[-1]
        if Entry.objects.filter(id = entry_id, visibility__in = ["PUBLIC", "UNLISTED"]).exists():
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
    author_fqid = "/".join(like_url.split("/")[:6])
    if Like.objects.filter(id = int(like_id), author = author_fqid):
        like_object = Like.objects.get(id = int(like_id), author = author_fqid)

        like_json = LikeSerializer(like_object)
        return Response(like_json.data)
    else:
        return Response(status = 404)

# Returns a paginated list of entries for a specific author
@api_view(['GET', 'POST'])
def ApiEntries(request, author_id):
    # Ensure the author exists before trying to fetch their entries
    author = get_object_or_404(Author, pk=author_id)
    
    if request.method == 'GET':
        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 5))
        
        # Query the entries
        # TODO: handle visibilities; currently only show PUBLIC posts and exclude DELETED posts.
        entries = Entry.objects.filter(author=author).exclude(visibility="DELETED").filter(visibility="PUBLIC").order_by('-published')
        
        # Paginate the queryset
        start = (page - 1) * size
        end = start + size
        paginated_entries = entries[start:end]
        
        # Package the data for EntriesSerializer
        data = {
            "page_number": page,
            "size": size,
            "count": entries.count(),
            "src": paginated_entries
        }
        
        # Serialize and return
        serializer = EntriesSerializer(data, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
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
    # Try to get the entry first
    # None if not found; avoid 404 immediately due to PUT-create behavior
    entry = Entry.objects.filter(pk=entry_id, author_id=author_id).first()

    if request.method == 'GET':
        # Cannot access deleted entries through the API
        if not entry or entry.visibility == "DELETED":
            return Response({"detail": "Not found."}, status=404)

        # Serialize and return
        serializer = EntrySerializer(entry, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Retrieve the logged-in author's ID from the session
        session_author_id = request.session.get("author_id")

        if str(session_author_id) != str(author_id):
            return Response(
                {"detail": "You do not have permission to modify this entry."}, 
                status=403
            )
        
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
        # Security check for deletion
        if str(request.session.get("author_id")) != str(author_id):
            return Response({"detail": "Forbidden"}, status=403)

        # Soft delete by changing visibility to DELETED
        entry.visibility = "DELETED"
        entry.save()
        
        return Response(status=204)

@api_view(['GET'])
def ApiEntryImage(request, author_id=None, entry_id=None):
    """
    Returns the raw image data for an entry.
    Allows Markdown to link to images.
    Supports both hierarchical and FQID style URLs.
    """
    # Get the entry
    entry = get_object_or_404(Entry, id=entry_id)

    # Check if base64 data, implying an image
    if ";base64" not in entry.contentType:
        return HttpResponse("This entry is not an image.", status=404)
    
    # Check if public entry or if user is authenticated
    if entry.visibility != "PUBLIC" and not request.user.is_authenticated:
        return HttpResponseForbidden("You do not have permission to view this image.")
    
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
def ApiEntryComments(request, author_id, entry_id):
    """
    Returns comments for an entry
    GET /api/authors/{author_id}/entries/{entry_id}/comments/
    """

    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    # Build FQID of the entry like your site uses
    base = request.build_absolute_uri('/')[:-1]
    entry_fqid = f"{base}/app/entry/{entry.id}/"

    comments = Comment.objects.filter(entry=entry_fqid).order_by("-published")

    serializer = CommentSerializer(comments, many=True)

    return Response({
        "type": "comments",
        "id": request.build_absolute_uri(),
        "page": 1,
        "size": comments.count(),
        "count": comments.count(),
        "src": serializer.data
    })

@api_view(["POST"])
def ApiAddComment(request, author_id, entry_id):
    """
    Create a comment on an entry
    POST /api/authors/{author_id}/entries/{entry_id}/comments/
    """

    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    author_url = request.data.get("author")
    comment_text = request.data.get("comment")

    if not author_url or not comment_text:
        return Response({"error": "Missing fields"}, status=400)

    base = request.build_absolute_uri('/')[:-1]
    entry_fqid = f"{base}/app/entry/{entry.id}/"

    new_comment = Comment.objects.create(
        id=f"{base}/comments/{uuid.uuid4()}",
        author=author_url,
        entry=entry_fqid,
        comment=comment_text,
        contentType=request.data.get("contentType", "text/plain"),
    )

    serializer = CommentSerializer(new_comment)

    return Response(serializer.data, status=201)
