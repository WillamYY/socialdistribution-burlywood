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


class RemoteFollow(models.Model):
    """
    Local author following a remote author (by FQID).
    Same semantics as Author.following for local authors.
    """
    follower = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='remote_following')
    followed_fqid = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed_fqid')


class RemoteFollowRequest(models.Model):
    """
    Follow request from a remote actor (they want to follow our local author).
    Shows up in Follow Requests so the target can approve/deny.
    actor_url: legacy/alternate column name (some deployments use this).
    """
    actor_fqid = models.URLField(max_length=500)
    actor_url = models.URLField(max_length=500, blank=True, null=True, db_column="actor_url")  # alias for armdb compatibility
    actor_display_name = models.CharField(max_length=255, blank=True, default="Remote author")
    target = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='remote_follow_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('actor_fqid', 'target')


class RemoteFollower(models.Model):
    """
    Remote actor follows our local author (approved).
    Friends = mutual follow: we follow them (RemoteFollow) and they follow us (RemoteFollower).
    actor_url: legacy/alternate column name (some deployments use this).
    """
    actor_fqid = models.URLField(max_length=500)
    actor_url = models.URLField(max_length=500, blank=True, null=True, db_column="actor_url")  # armdb compatibility
    actor_display_name = models.CharField(max_length=255, blank=True, default="Remote author")
    target = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='remote_followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('actor_fqid', 'target')


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

class AdminHostedImage(models.Model):
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50, blank=True, null=True)
    content = models.TextField(blank=True, null=True)    # base64 string
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

"""
Creates a class that handles the nodes that we want to pull information from
"""
class IncomingNode(models.Model):
    id = models.AutoField(primary_key = True)
    url = models.URLField(unique = True)
    username = models.CharField(max_length = 30, default = "")
    password = models.CharField(max_length = 30, default = "")

"""
Creates a class that handles the nodes that want to pull information from us
"""
class OutgoingNode(models.Model):
    id = models.AutoField(primary_key = True)
    url = models.URLField(unique = True)
    username = models.CharField(max_length = 30, default = "")
    password = models.CharField(max_length = 30, default = "")
    is_active = models.BooleanField(default=True)