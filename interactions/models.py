from django.db import models
from django.utils import timezone

# Model for managing social comments on entries via FQIDs
class Comment(models.Model):
    type = "comment"

    id = models.URLField(primary_key=True, max_length=500)
    author = models.URLField(max_length=500)
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


# Model for managing likes on entries or comments via FQIDs
class Like(models.Model):
    type = "like"

    id = models.URLField(primary_key=True, max_length=500)
    author = models.URLField(max_length=500)
    object = models.URLField(max_length=500)
    published = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("author", "object")
        ordering = ["-published"]

    def __str__(self):
        return f"Like by {self.author} on {self.object}"