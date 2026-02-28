from rest_framework import serializers
from .models import Like, Author

"""
Serializes author objects
"""
class AuthorSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "author") # Sets the type to author in the response
    displayName = serializers.CharField(source = "name") # Maps the displayName field to the name field in the database
    profileImage = serializers.URLField(source = "picture") # Maps the profileImage field to the picture field in the database
    id = serializers.SerializerMethodField() # Turns the interger id into a url

    class Meta():
        # Maps to the model object in the database
        model = Author
        fields = ["type","id","host","displayName","github","profileImage","web"] # Sets all of the fields

    # Defines how to create the id
    def get_id(self,obj):
        return f"{obj.host}authors/{obj.id}"

"""
Serializes a singular like
"""
class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default = "like") # Sets the type of the serializer to like
    author = AuthorSerializer(source = "user")
    published = serializers.DateTimeField(source = "time") # Attaches published to the time field
    object = serializers.SerializerMethodField() # Stores the object so that it can be displayed even though it does not go in the database

    class Meta():
        model = Like
        fields = ["type","author","published","id","object"]
    
    # Returns the url of the object that was liked
    def get_object(self,obj):
        return self.context["object"]

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
