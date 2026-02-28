from django.db import models
import uuid
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.
"""
Author model uniquely identifies each author and stores profile details.
"""
class Author(models.Model):
    id = models.AutoField(primary_key=True)               # Unique ID for consistent URLs
    username = models.CharField(max_length=40, unique=True)  # Login ID
    password = models.CharField(max_length=128)           # Hashed password
    name = models.CharField(max_length=40, blank=True)   # Display name / editable
    description = models.TextField(blank=True)            # Bio
    picture = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True)                  # GitHub link
    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True
    )
    host = models.URLField(blank=True)
    web = models.URLField(blank=True)

    def __str__(self):
        return self.username

    # Helper methods for password
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def friends(self):
        """
        Returns a queryset of authors where both authors follow each other.
        """
        return self.followers.filter(followers=self)

"""
Creates a class for the request to create a new author
"""
class AuthorRequest(models.Model):
    id = models.AutoField(primary_key = True) # Makes each request unique
    username = models.CharField(max_length=40, unique=True)  # Login ID
    password = models.CharField(max_length=40)           # Hashed password
    name = models.CharField(max_length = 40,default = "user") # Display name
    github = models.URLField(blank=True)
    picture = models.URLField(blank=True, null=True)
    host = models.URLField(blank=True)
    web = models.URLField(blank=True)
    

class Entry(models.Model):
    type = "entry"
    title = models.CharField(max_length=255)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    web = None  # 
    description = models.TextField()

    CONTENT_TYPE_CHOICES = [
        ("text/markdown", "Markdown"),
        ("text/plain", "Plain Text"),
        ("application/base64", "Application/Base64"),
        ("image/png;base64", "PNG Image"),
        ("image/jpeg;base64", "JPEG Image"),
    ]
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()

    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    # TODO: comments and likes
    comments = None
    likes = None
    published = models.DateTimeField(auto_now_add=True)

    VISIBILITY_CHOICES = [
        ("PUBLIC", "Public"),
        ("FRIENDS", "Friends Only"),
        ("UNLISTED", "Unlisted"),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="PUBLIC")
    
"""
Class for likes attachedto an entry
"""
class Like(models.Model):
    id = models.AutoField(primary_key = True)
    entry = models.ForeignKey("Entry", on_delete=models.CASCADE)
    user = models.ForeignKey("Author", on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add = True)