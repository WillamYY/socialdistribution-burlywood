"""
Approve or reject AuthorRequest signups (same behavior as Django admin actions).
"""
from django.db import transaction

from .models import Author, AuthorRequest


def approve_author_request(ar: AuthorRequest, request):
    """
    Create Author from pending AuthorRequest and remove the request.
    """
    if Author.objects.filter(username=ar.username).exists():
        raise ValueError("An author with this username already exists.")

    with transaction.atomic():
        author = Author(
            username=ar.username,
            name=ar.name or ar.username,
            github=ar.github or "",
            picture_url=ar.picture_url or "",
            host=ar.host or f"https://{request.get_host()}/api",
        )
        if ar.picture:
            author.picture_url = author.picture_url or ar.picture
        author.set_password(ar.password)
        author.save()
        base = request.build_absolute_uri("/").rstrip("/")
        author.web = f"{base}/app/user/{author.id}"
        author.save(update_fields=["web"])
        ar.delete()


def reject_author_request(ar: AuthorRequest):
    ar.delete()
