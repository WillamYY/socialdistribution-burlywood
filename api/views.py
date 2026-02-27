# Create your views here.
import base64
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render,get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Author
from entries.models import Entry, Like
from .serializers import LikesSerializer, LikeSerializer, EntrySerializer, EntriesSerializer

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
        authorInfo = {"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture,"web":author.web}
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
        authorInfo = {"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture,"web":author.web}
        return Response(authorInfo)
    elif request.method == "PUT":
        # Replaces the object if it is put on top of
        if not Author.objects.filter(id = id).exists():
            # Ensures that the authors id matches the correct Id of where it is being placed and that the name is unique
            if str(id) == request.data.get("id").split("/")[-1] and not Author.objects.filter(name = request.data.get("displayName")).exists():
                author = Author(id = id,host = request.data.get("host"),name = request.data.get("displayName"),github = request.data.get("github"),picture = request.data.get("profileImage"),web = request.data.get("web"))
                author.save()
                authorID = author.host + "authors/" + str(author.id)
                return Response({"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture,"web":author.web})
            # If the authors Id is invalid return a 400 respose
            else:
                return Response(status = 400)
        # If the user does exist replace it's info with the new info
        else:
            # Ensures that the authors id matches the correct Id of where it is being placed
            if str(id) == request.data.get("id").split("/")[-1]:
                # If an author already exists with the name that is not the current author return a error code of 400
                if Author.objects.filter(name = request.data.get("displayName")).exists():
                    if get_object_or_404(Author,name=request.data.get("displayName")).id != id:
                        return Response(status = 400)
                author = get_object_or_404(Author,pk=id) # Gets the author
                # Updates the authors info
                author.id = id
                author.host = request.data.get("host")
                author.name = request.data.get("displayName")
                author.github = request.data.get("github")
                author.picture = request.data.get("profileImage")
                author.web = request.data.get("web")
                author.save()
                # Turns the authors id into it's string
                authorID = author.host + "authors/" + str(author.id)
                return Response({"type":"author","id": authorID,"host": author.host,"displayName": author.name, "github":author.github, "profileImage":author.picture,"web":author.web})
            else:
                return Response(status = 400)
    # Returns a 405 error if using invalid method
    else:
        return Response(status = 405)

# Returns who liked a specific entry with author described
@api_view(["GET"])
def ApiAuthorAndEntryLikes(request,author_id,entry_id):
    # Ensures the entry exists before accessing it
    if Entry.objects.filter(id = entry_id).exists():
        entry = Entry.objects.get(id = entry_id)
        likes = Like.objects.filter(entry = entry)
        # Finds the link to the object that was liked
        entryURL = request.build_absolute_uri()
        # Serializes the data
        likesSerializer = LikesSerializer({"page_number":1,"size":5,"count":likes.count(),"src":likes},context = {"link":entryURL})
        return Response(likesSerializer.data)
    else:
        # Returns 404 if the entry does not exist
        return Response(status = 404)

# Returns who liked a specific entry with no author
@api_view(["GET"])
def ApiEntryLikes(request,entry_id):
    # Ensures the entry exists before accessing it
    if Entry.objects.filter(id = entry_id).exists():
        entry = Entry.objects.get(id = entry_id)
        likes = Like.objects.filter(entry = entry)
        # Finds the link to the object that was liked
        entryURL = request.build_absolute_uri()
        # Serializes the data
        likesSerializer = LikesSerializer({"page_number":1,"size":5,"count":likes.count(),"src":likes},context = {"link":entryURL})
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