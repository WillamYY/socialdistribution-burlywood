"""
Directory / profile visibility for superuser-linked Author rows only.
Regular authors are always listed and discoverable; `listed_publicly` is ignored for them.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q

from .node_admin_auth import is_node_admin


def superuser_usernames():
    User = get_user_model()
    return list(User.objects.filter(is_superuser=True).values_list("username", flat=True))


def is_superuser_linked_author(author) -> bool:
    """True if this Author row corresponds to a Django superuser (same username)."""
    if not author or not getattr(author, "username", None):
        return False
    User = get_user_model()
    return User.objects.filter(username=author.username, is_superuser=True).exists()


def authors_for_public_directory_qs():
    """
    Authors shown on Home (this node) and in GET /api/authors/.
    Non–superuser authors: always included. Superuser authors: only if listed_publicly.
    """
    from .models import Author

    supers = superuser_usernames()
    if not supers:
        return Author.objects.all()
    return Author.objects.filter(
        ~Q(username__in=supers) | Q(username__in=supers, listed_publicly=True)
    )


def author_profile_visible_to_viewer(request, author) -> bool:
    """Web profile: hidden only for superuser-linked authors with listed_publicly=False."""
    if not is_superuser_linked_author(author):
        return True
    if getattr(author, "listed_publicly", True):
        return True
    viewer_id = request.session.get("author_id")
    if viewer_id is not None and int(viewer_id) == int(author.id):
        return True
    if is_node_admin(request):
        return True
    return False
