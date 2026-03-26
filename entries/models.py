import uuid
from django.db import models

class Entry(models.Model):
    """
    Local entry created on the local node.
    """
    title = models.CharField(max_length=255)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField()
    fqid = models.URLField(null=True, blank=True)

    CONTENT_TYPE_CHOICES = [
        ("text/markdown", "Markdown"),
        ("text/plain", "Plain Text"),
        ("application/base64", "Application/Base64"),
        ("image/png;base64", "PNG Image"),
        ("image/jpeg;base64", "JPEG Image"),
    ]
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()
    content_raw = models.TextField(blank=True, null=True)    # Store Markdown raw text

    author = models.ForeignKey("core.Author", on_delete=models.CASCADE)
    published = models.DateTimeField(auto_now_add=True)

    VISIBILITY_CHOICES = [
        ("PUBLIC", "Public"),
        ("FRIENDS", "Friends Only"),
        ("UNLISTED", "Unlisted"),
        ("DELETED", "Deleted"),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="PUBLIC")

    # For GitHub activity sync (User Story #5): avoid importing same event twice
    github_event_id = models.BigIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.title

class RemoteEntry(models.Model):
    """
    Remote entry delivered to local authors through inbox.
    """
    recipient = models.ForeignKey(
        "core.Author",
        on_delete=models.CASCADE,
        related_name="inbox_remote_entries",
    )

    # Remote entry info
    fqid = models.URLField(max_length=500)
    web = models.URLField(max_length=500, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    contentType = models.CharField(max_length=50, choices=Entry.CONTENT_TYPE_CHOICES, default="text/plain")
    content = models.TextField(blank=True)
    content_raw = models.TextField(blank=True, null=True)    # Store Markdown raw text
    published = models.DateTimeField(null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=Entry.VISIBILITY_CHOICES, default="PUBLIC")

    # Remote author info
    author_fqid = models.URLField(max_length=500)
    author_host = models.URLField(max_length=500, blank=True)
    author_display_name = models.CharField(max_length=255, blank=True, default="Remote author")
    author_github = models.URLField(blank=True)
    author_profile_image = models.URLField(blank=True)

    # Raw json object
    raw_author = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    # Timestamp
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensure no duplicates
        unique_together = ("recipient", "fqid")
        # Set default order 
        ordering = ["-published", "-updated_at"]

    def __str__(self):
        return self.fqid