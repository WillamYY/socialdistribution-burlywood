from rest_framework import serializers
from .models import Like, Author

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
class LikeSerializer(serializers.Serializer):
    type = serializers.CharField(default="Like")
    id = serializers.URLField()
    author = serializers.URLField()
    object = serializers.URLField()
    published = serializers.DateTimeField()

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
