from rest_framework import serializers
from core.models import Author
from entries.models import Entry
from interactions.models import Like, Comment
import re

"""
Serializes author objects
"""
class AuthorSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "author") # Sets the type to author in the response
    displayName = serializers.SerializerMethodField() # Maps the displayName field to the name field in the database
    profileImage = serializers.URLField(source = "picture") # Maps the profileImage field to the picture field in the database
    id = serializers.SerializerMethodField() # Turns the interger id into a url

    host = serializers.URLField()
    web = serializers.URLField()

    class Meta():
        # Maps to the model object in the database
        model = Author
        fields = ["type","id","host","displayName","github","profileImage","web"] # Sets all of the fields

    # Defines how to create the id
    def get_id(self, obj):
        host = (obj.host or "").rstrip("/")

        # host already includes /api
        if host.endswith("/api"):
            return f"{host}/authors/{obj.id}"

        # host is plain domain
        return f"{host}/api/authors/{obj.id}"
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        host = data.get("host") or "http://127.0.0.1:8000/"
        host = host.rstrip("/")

        # normalize host to end with /api
        if not host.endswith("/api"):
            host = f"{host}/api"

        data["host"] = host

        # rebuild id from normalized host so it never becomes api//authors
        data["id"] = f"{host}/authors/{instance.id}"

        return data
    
    def get_displayName(self, obj):
        if obj.name:
            return obj.name
        return obj.username

"""
Serializes a singular like
"""
class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "like") # Sets the type of the serializer to like
    id = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    published = serializers.DateTimeField() # Attaches published to the time field
    object = serializers.URLField() # Stores the object so that it can be displayed even though it does not go in the database

    class Meta():
        model = Like
        fields = ["type","author","published","id","object"]

    # Turns ID into URL
    def get_id(self, obj):
        author = self.get_author(obj)
        like_uuid = getattr(obj, "uuid", None)

        if like_uuid:
            like_uuid = str(like_uuid)
        else:
            like_uuid = str(obj.id).rstrip("/").split("/")[-1]

        author_id = str(author["id"]).rstrip("/")
        return f"{author_id}/liked/{like_uuid}"

    # Serializes the author
    def get_author(self, obj):
        author_url = (obj.author or "").rstrip("/")

        # Try to parse a local integer author id safely
        author_url = author_url.replace("://", "§§TEMP§§").replace("//", "/").replace("§§TEMP§§", "://")

        author_id_part = author_url.split("/")[-1]
        author_obj = None

        if author_id_part.isdigit():
            author_obj = Author.objects.filter(id=int(author_id_part)).first()

        if not author_obj:
            return {
                "type": "author",
                "id": obj.author,
                "host": "",
                "displayName": author_id_part if author_id_part else "Unknown",
                "github": "",
                "profileImage": "",
                "web": ""
            }

        data = AuthorSerializer(author_obj).data

        if not data.get("displayName"):
            data["displayName"] = author_obj.username

        if not data.get("host"):
            data["host"] = "http://127.0.0.1:8000/"

        return data

"""
Creates the serializer for multiple likes
"""
class LikesSerializer(serializers.Serializer):
    type = serializers.CharField(default="likes") # Sets the type of serializer to likes
    web = serializers.SerializerMethodField() # Uses the get_web function to serialize what web is
    id = serializers.SerializerMethodField()  # Uses the get_id function to serialize what ID is
    # Stores the page number, size, and count to display when serializing
    page_number = serializers.IntegerField()
    size = serializers.IntegerField()
    count = serializers.IntegerField()
    # Stores the multiple likes
    src = LikeSerializer(many=True)

    
    def get_web(self,obj):
        # Replaces the api folder with our app folder
        main_web_page = self.context["link"].replace("/api/","/app/")
        # Changes the url so authors is singular
        main_web_page = main_web_page.replace("/authors/","/author/")
        # Slices off the likes from the url
        return main_web_page[:-len("/likes")]

    # Returns the id from the api
    def get_id(self,obj):
        return self.context["link"]

class CommentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="comment", read_only=True)
    author = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "type",
            "id",
            "author",
            "comment",
            "contentType",
            "published",
        ]

    def get_id(self, obj):
        # If your Comment model already stores a URL id, use that
        if isinstance(obj.id, str) and obj.id.startswith("http"):
            return obj.id

        # Fallback: try to construct from object field if it exists
        object_url = getattr(obj, "object", None)
        if object_url:
            return f"{str(object_url).rstrip('/')}/comments/{obj.id}"

        return str(obj.id)

    def get_author(self, obj):
        author_value = getattr(obj, "author", None)

        # If author is already a local Author object
        if isinstance(author_value, Author):
            return AuthorSerializer(author_value).data

        # If author is stored as a URL string
        if isinstance(author_value, str):
            author_url = author_value.rstrip("/")
            author_url = author_url.replace("://", "§§TEMP§§").replace("//", "/").replace("§§TEMP§§", "://")
            author_id_part = author_url.split("/")[-1]

            if author_id_part.isdigit():
                author_obj = Author.objects.filter(id=int(author_id_part)).first()
                if author_obj:
                    return AuthorSerializer(author_obj).data

            return {
                "type": "author",
                "id": author_value,
                "host": "",
                "displayName": author_id_part if author_id_part else "Unknown",
                "github": "",
                "profileImage": "",
                "web": ""
            }

        return None
    
class EntrySerializer(serializers.ModelSerializer):
    """
    Serializes a singular Entry.
    """
    type = serializers.CharField(default="entry", read_only=True)
    author = AuthorSerializer(read_only=True)
    
    # Set up serializer for fields with dynamic URLs and logics
    id = serializers.SerializerMethodField()
    web = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Entry
        fields = [
            "type", "title", "id", "web", "description", "contentType", "content", 
            "author", "comments", "likes", "published", "visibility"
        ]

    def get_id(self, obj):
        """
        Getter for the id (api-facing url).
        """
        request = self.context.get('request')
        if request:
            # Must be the original URL on the node the entry came from
            return request.build_absolute_uri(f"/api/authors/{obj.author.id}/entries/{obj.id}/")
        # Fallback if no request context
        return f"/api/authors/{obj.author.id}/entries/{obj.id}/" 

    def get_web(self, obj):
        """
        Getter for the web (human-facing html page).
        """
        request = self.context.get('request')
        if request:
            # URL of the user's HTML profile page
             return request.build_absolute_uri(f"/app/entry/{obj.id}/")
        # Fallback if no request context
        return f"/app/entry/{obj.id}/"

    def get_comments(self, obj):
        """
        Getter for the comments on this entry.
        """
        base_url = self.get_id(obj).rstrip("/")
        web_url = self.get_web(obj).rstrip("/")

        # Try a few common object values
        possible_objects = [
            base_url,
            f"{base_url}/",
            str(obj.id),
        ]

        comments_qs = Comment.objects.none()

        # If Comment model has an 'object' field, use it
        if hasattr(Comment, "object"):
            comments_qs = Comment.objects.filter(object__in=possible_objects).order_by("-published")

        serialized_comments = CommentSerializer(comments_qs[:50], many=True, context=self.context).data

        return {
            "type": "comments",
            "id": f"{base_url}/comments",
            "web": f"{web_url}/comments",
            "page_number": 1,
            "size": 50,
            "count": comments_qs.count(),
            "src": serialized_comments,
        }

    def get_likes(self, obj):
        """
        Getter for the likes on this entry.
        """
        # Construct the base URL for the likes endpoint
        base_url = self.get_id(obj)
        
        likes_url = f"{base_url}likes" 
        # Handles both http and http requests
        search = re.search("entr(?:y|ies)/([^/]+)",base_url)
        # Prevents crashes
        if not search:
            entry_likes = []
        else:
            # Handles both the no slash and slash version
            if search.group(1)[-1] == "/":
                alt = search.group(1)[:-1]
            else:
                alt = search.group(1) + "/"
            print(search.group(1),alt)
            # Query the database for likes on this entry
            entry_likes = Like.objects.filter(object__endswith=search.group(1)) | Like.objects.filter(object__endswith=alt)
        
        # Package the data for LikesSerializer
        likes_data = {
            "page_number": 1,
            "size": 50,
            "count": entry_likes.count(),
            "src": entry_likes
        }
        
        # Instantiate LikesSerializer
        serializer = LikesSerializer(likes_data, context={"link": likes_url})
        
        # Return the fully formed JSON dictionary
        return serializer.data

    
class EntriesSerializer(serializers.Serializer):
    """
    Serializes multiple entries.
    """
    type = serializers.CharField(default="entries")
    page_number = serializers.IntegerField()
    size = serializers.IntegerField()
    count = serializers.IntegerField()
    src = EntrySerializer(many=True)