from rest_framework import serializers
from .models import Author
from entries.models import Entry
from interactions.models import Like

"""
Serializes author objects
"""
class AuthorSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "Author") # Sets the type to author in the response
    displayName = serializers.CharField(source = "name") # Maps the displayName field to the name field in the database
    profileImage = serializers.URLField(source = "picture") # Maps the profileImage field to the picture field in the database

    class Meta():
        # Maps to the model object in the database
        model = Author
        fields = ["type","id","host","displayName","github","profileImage","web"] # Sets all of the fields

"""
Serializes a singular like
"""
class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "Like") # Sets the type of the serializer to like
    author = AuthorSerializer(source = "user")
    published = serializers.DateTimeField(source = "time") # Attaches published to the time field
    object = serializers.SerializerMethodField() # Stores the object so that it can be displayed even though it does not go in the database

    class Meta():
        model = Like
        fields = ["type","author","published","id","object"]
    
    # Returns the url of the object that was liked
    def get_object(self,obj):
        return self.context["link"]

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
             return request.build_absolute_uri(f"/app/authors/{obj.author.id}/entries/{obj.id}/")
        # Fallback if no request context
        return f"/app/authors/{obj.author.id}/entries/{obj.id}/"

    def get_comments(self, obj):
        """
        Getter for the comments on this entry.
        """
        # The comments object structure
        # TODO: Implement actual comment fetching logic
        base_url = self.get_id(obj)
        web_url = self.get_web(obj)
        return {
            "type": "comments",
            "id": f"{base_url}comments",
            "web": f"{web_url}comments",
            "page_number": 1,
            "size": 5,
            "count": 0, # TODO: actual count
            "src": [] # TODO: actual serialized comments
        }

    def get_likes(self, obj):
        """
        Getter for the likes on this entry.
        """
        # Construct the base URL for the likes endpoint
        base_url = self.get_id(obj)
        
        likes_url = f"{base_url}likes" 
        
        # Query the database for likes on this entry
        entry_likes = Like.objects.filter(object=base_url)
        
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