from django.db import models
from django.utils import timezone

class Comment(models.Model):
    type = "comment"

    # Fully Qualified ID (global, unique URL)
    id = models.URLField(primary_key=True, max_length=500)

    # Author FQID (URL string — supports remote authors)
    author = models.URLField(max_length=500)

    # Entry FQID this comment belongs to (URL string)
    entry = models.URLField(max_length=500)
    comment = models.TextField()

    CONTENT_TYPE_CHOICES = [
        ("text/plain", "Plain Text"),
        ("text/markdown", "Markdown"),
    ]
    contentType = models.CharField(
        max_length=50,
        choices=CONTENT_TYPE_CHOICES,
        default="text/plain"
    )
    web = models.URLField(max_length=500, blank=True, null=True)
    published = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published"]

    def __str__(self):
        return f"Comment by {self.author} on {self.entry}"


class Like(models.Model):
    """
    Spec-compliant Like model.
    Handles likes for BOTH Entries and Comments.
    """
    type = "like"

    # Fully Qualified ID (global, unique URL of the like itself)
    id = models.URLField(primary_key=True, max_length=500)

    # Author FQID (URL string of the person who clicked like)
    author = models.URLField(max_length=500)

    # The FQID URL of the object being liked (Can be an Entry URL OR a Comment URL)
    object = models.URLField(max_length=500)

    # ISO 8601 timestamp
    published = models.DateTimeField(default=timezone.now)

    class Meta:
        # Prevent the same author from liking the exact same object twice
        unique_together = ("author", "object")
        ordering = ["-published"]

    def __str__(self):
        return f"Like by {self.author} on {self.object}"