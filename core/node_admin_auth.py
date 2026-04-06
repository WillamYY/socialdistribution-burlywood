"""
Gate in-app node admin to Django superusers (same accounts as /admin/).
"""
from functools import wraps

from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages


def is_node_admin(request):
    if not request.session.get("author_id"):
        return False
    pk = request.session.get("django_superuser_pk")
    if not pk:
        return False
    User = get_user_model()
    return User.objects.filter(pk=pk, is_superuser=True).exists()


def node_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("author_id"):
            return redirect("Login")
        if not is_node_admin(request):
            messages.error(request, "Node admin access requires a Django superuser login.")
            return redirect("NodeDisplay")
        return view_func(request, *args, **kwargs)

    return _wrapped
