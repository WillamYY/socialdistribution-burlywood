import uuid
from django.db import models
from core.models import Author

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
    content_raw = models.TextField(blank=True, null=True)    # Store Markdown raw text

    author = models.ForeignKey("core.Author", on_delete=models.CASCADE)
    published = models.DateTimeField(auto_now_add=True)

    VISIBILITY_CHOICES = [
        ("PUBLIC", "Public"),
        ("FRIENDS", "Friends Only"),
        ("UNLISTED", "Unlisted"),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="PUBLIC")

    def __str__(self):
        return self.title