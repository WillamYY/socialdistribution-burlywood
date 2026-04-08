import re

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from entries.models import Entry
from entries.views import update_entry_from_request, get_admin_hosted_images
from core.remote import federate_entry_create_or_update, federate_entry_deleted

from .models import Author, AuthorRequest, IncomingNode, OutgoingNode
from .author_visibility import is_superuser_linked_author, superuser_usernames
from .node_admin_auth import node_admin_required
from .signup_approval import approve_author_request, reject_author_request
from .validators import validate_username, validate_password

NODE_URL_RE = re.compile(r"^https?://[^/]+/$")


def _node_url_ok(url):
    return bool(NODE_URL_RE.match(url or ""))


@node_admin_required
def node_admin_dashboard(request):
    admin_author = Author.objects.get(pk=request.session["author_id"])
    return render(
        request,
        "node_admin/dashboard.html",
        {
            "admin_author": admin_author,
            "admin_is_superuser_author": is_superuser_linked_author(admin_author),
            "author_count": Author.objects.count(),
            "pending_signups": AuthorRequest.objects.count(),
            "entry_count": Entry.objects.exclude(visibility="DELETED").count(),
            "incoming_count": IncomingNode.objects.count(),
            "outgoing_count": OutgoingNode.objects.count(),
        },
    )


@node_admin_required
@require_POST
def node_admin_set_listed_publicly(request):
    author = Author.objects.get(pk=request.session["author_id"])
    if not is_superuser_linked_author(author):
        messages.error(
            request,
            "Directory visibility only applies to your Django superuser account.",
        )
        return redirect("node_admin_dashboard")
    author.listed_publicly = request.POST.get("listed_publicly") == "1"
    author.save(update_fields=["listed_publicly"])
    if author.listed_publicly:
        messages.success(
            request,
            "Your account is listed on Home and in /api/authors/ so others (and remote nodes) can discover you.",
        )
    else:
        messages.success(
            request,
            "Your account is hidden from the public author directory and API list. You still have full access when logged in.",
        )
    return redirect("node_admin_dashboard")


@node_admin_required
def node_admin_signups(request):
    rows = AuthorRequest.objects.order_by("id")
    return render(request, "node_admin/signups.html", {"requests": rows})


@node_admin_required
@require_POST
def node_admin_signup_approve(request, pk):
    ar = get_object_or_404(AuthorRequest, pk=pk)
    un = ar.username
    try:
        approve_author_request(ar, request)
        messages.success(request, f"Approved {un} — they can log in now.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("node_admin_signups")


@node_admin_required
@require_POST
def node_admin_signup_reject(request, pk):
    ar = get_object_or_404(AuthorRequest, pk=pk)
    un = ar.username
    reject_author_request(ar)
    messages.info(request, f"Rejected signup for {un}.")
    return redirect("node_admin_signups")


@node_admin_required
def node_admin_authors(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        name = (request.POST.get("name") or "").strip() or username

        ok, err = validate_username(username)
        if not ok:
            messages.error(request, err)
            return redirect("node_admin_authors")
        ok, err = validate_password(password)
        if not ok:
            messages.error(request, err)
            return redirect("node_admin_authors")
        if Author.objects.filter(username=username).exists() or AuthorRequest.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("node_admin_authors")

        author = Author(
            username=username,
            name=name,
            host=f"https://{request.get_host()}/api",
        )
        author.set_password(password)
        author.save()
        base = request.build_absolute_uri("/").rstrip("/")
        author.web = f"{base}/app/user/{author.id}"
        author.save(update_fields=["web"])
        messages.success(request, f"Created author {username}.")
        return redirect("node_admin_authors")

    authors = Author.objects.order_by("username")
    return render(
        request,
        "node_admin/authors.html",
        {
            "authors": authors,
            "super_usernames": set(superuser_usernames()),
        },
    )


@node_admin_required
@require_POST
def node_admin_author_delete(request, pk):
    if pk == request.session.get("author_id"):
        messages.error(request, "You cannot delete your own account from the node admin panel.")
        return redirect("node_admin_authors")
    author = get_object_or_404(Author, pk=pk)
    un = author.username
    author.delete()
    messages.success(request, f"Removed author {un} and their related data.")
    return redirect("node_admin_authors")


@node_admin_required
def node_admin_entries(request):
    entries = (
        Entry.objects.select_related("author")
        .order_by("-published")
    )
    return render(request, "node_admin/entries.html", {"entries": entries})


@node_admin_required
def node_admin_entry_edit(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id)
    cancel_url = reverse("node_admin_entries")

    if request.method == "POST":
        success, error_msg = update_entry_from_request(request, entry)
        if not success:
            messages.error(request, error_msg)
            return render(
                request,
                "entries/edit_entry.html",
                {
                    "entry": entry,
                    "admin_hosted_images": get_admin_hosted_images(request),
                    "cancel_url": cancel_url,
                    "page_hero_title": "Edit entry (admin)",
                    "page_hero_sub": f"Author: {entry.author.username}",
                },
            )
        entry.published = timezone.now()
        entry.save()
        federate_entry_create_or_update(entry, request)
        messages.success(request, "Entry updated.")
        return redirect("node_admin_entries")

    return render(
        request,
        "entries/edit_entry.html",
        {
            "entry": entry,
            "admin_hosted_images": get_admin_hosted_images(request),
            "cancel_url": cancel_url,
            "page_hero_title": "Edit entry (admin)",
            "page_hero_sub": f"Author: {entry.author.username}",
        },
    )


@node_admin_required
@require_POST
def node_admin_entry_delete(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id)
    entry.visibility = "DELETED"
    entry.save()
    federate_entry_deleted(entry, request)
    messages.success(request, "Entry marked deleted and federated.")
    return redirect("node_admin_entries")


@node_admin_required
def node_admin_incoming_nodes(request):
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        if not _node_url_ok(url):
            messages.error(
                request,
                "URL must look like https://hostname/ with a trailing slash.",
            )
            return redirect("node_admin_incoming_nodes")
        ok, err = validate_password(password)
        if not ok:
            messages.error(request, err)
            return redirect("node_admin_incoming_nodes")
        if IncomingNode.objects.filter(url=url).exists():
            messages.error(request, "That incoming node URL is already registered.")
            return redirect("node_admin_incoming_nodes")
        IncomingNode.objects.create(url=url, username=username, password=password)
        messages.success(request, "Incoming node added.")
        return redirect("node_admin_incoming_nodes")

    nodes = IncomingNode.objects.order_by("url")
    return render(request, "node_admin/nodes_incoming.html", {"nodes": nodes})


@node_admin_required
@require_POST
def node_admin_incoming_delete(request, pk):
    get_object_or_404(IncomingNode, pk=pk).delete()
    messages.success(request, "Incoming node removed.")
    return redirect("node_admin_incoming_nodes")


@node_admin_required
def node_admin_outgoing_nodes(request):
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        is_active = request.POST.get("is_active") == "1"
        if not _node_url_ok(url):
            messages.error(
                request,
                "URL must look like https://hostname/ with a trailing slash.",
            )
            return redirect("node_admin_outgoing_nodes")
        ok, err = validate_password(password)
        if not ok:
            messages.error(request, err)
            return redirect("node_admin_outgoing_nodes")
        if OutgoingNode.objects.filter(url=url).exists():
            messages.error(request, "That outgoing node URL is already registered.")
            return redirect("node_admin_outgoing_nodes")
        OutgoingNode.objects.create(
            url=url, username=username, password=password, is_active=is_active
        )
        messages.success(request, "Outgoing node added.")
        return redirect("node_admin_outgoing_nodes")

    nodes = OutgoingNode.objects.order_by("url")
    return render(request, "node_admin/nodes_outgoing.html", {"nodes": nodes})


@node_admin_required
@require_POST
def node_admin_outgoing_delete(request, pk):
    get_object_or_404(OutgoingNode, pk=pk).delete()
    messages.success(request, "Outgoing node removed.")
    return redirect("node_admin_outgoing_nodes")
