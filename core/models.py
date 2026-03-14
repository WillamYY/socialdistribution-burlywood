from django.db import models
from django.contrib.auth.hashers import make_password, check_password

"""
Author model uniquely identifies each author and stores profile details.
"""
class Author(models.Model):
    id = models.AutoField(primary_key=True)               # Unique ID for consistent URLs
    username = models.CharField(max_length=40, unique=True)  # Login ID
    password = models.CharField(max_length=128)           # Hashed password
    name = models.CharField(max_length=40, blank=True)   # Display name / editable
    description = models.TextField(blank=True)            # Bio
    picture = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    picture_url = models.URLField(blank=True)
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
    
class FollowRequest(models.Model):
    requester = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='sent_requests')
    target = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='received_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('requester', 'target')  # prevent duplicate requests

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
    picture_url = models.URLField(blank=True)
    host = models.URLField(blank=True)
    web = models.URLField(blank=True)

class HostedImage(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='hosted_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
        
    def get_markdown_link(self):
        # A handy property to show the admin exactly what to copy/paste
        return f"![{self.title}](/media/{self.image.name})"