# Create your views here.
from django.shortcuts import render,get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Author, Entry, Like, AuthorRequest
from .serializers import LikesSerializer, LikeSerializer

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
            if str(id) == request.data.get("id").split("/")[-1] and not Author.objects.filter(username = request.data.get("displayName")).exists():
                # Creates an author request with the information
                author = AuthorRequest(id = id,username = request.data.get("displayName"),name = request.data.get("displayName"),github = request.data.get("github"),picture = request.data.get("profileImage"),web = request.data.get("web"),host = request.data.get("host") )
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
        likesSerializer = LikesSerializer({"page_number":1,"size":5,"count":likes.count(),"src":likes},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
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
        likesSerializer = LikesSerializer({"page_number":1,"size":5,"count":likes.count(),"src":likes},context = {"link":entryURL,"object":entryURL[:-len("/likes")]})
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
            like = Like(entry = entry, user = likeAuthor)
            like.save()
            like_serializer = LikeSerializer({"user":like.user,"time":like.time},context = {"object":request.data.get("object")})
            return Response(like_serializer.data)
    else:
        return Response(status = 404)
    
@api_view(["GET"])
def ApiAuthorLiked(request, author_id):
    pass

@api_view(["GET"])
def ApiSingleLikeRemoteLocal(request, author_id, like_url):
    pass

@api_view(["GET"])
def ApiSingleLikeLocal(request, like_url):
    like_id = like_url.split("/")[-1]
    print(like_id)
    like_object = get_object_or_404(Like, pk = int(like_id))
    print(like_object)
    #print(like_object)
    print(like_object.entry)
    like_data = LikeSerializer(like_object, context = {"object":None})
    print(like_data.data)
    return Response(status = 200)
