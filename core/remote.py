"""
Fetch remote public entries from IncomingNode nodes.
Uses same approach as RemoteProfileDisplay - authors from /api/authors/, entries from /api/authors/{id}/entries/
"""
import json
import re
import requests
from types import SimpleNamespace
import logging
from api.serializers import EntrySerializer
from core.models import RemoteFollow, RemoteFollower, EntryDelivery, IncomingNode

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def _absolute_remote_url(node_base: str, url_or_path: str) -> str:
    """
    Remote APIs often return id/web as paths like /app/authors/1/entries/<uuid>/.
    Without a scheme+host, the browser resolves them on OUR node → 404.
    """
    s = (url_or_path or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    base = (node_base or "").rstrip("/")
    if not base:
        return s
    if s.startswith("/"):
        return f"{base}{s}"
    return f"{base}/{s}"


def _resolve_entry_fqid(node_base: str, author_num_id: str, eid_raw) -> str:
    """Canonical absolute URL for a remote entry (API id)."""
    s = str(eid_raw or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/"):
        return _absolute_remote_url(node_base, s)
    if _UUID_RE.match(s):
        return f"{node_base.rstrip('/')}/api/authors/{author_num_id}/entries/{s}"
    return _absolute_remote_url(node_base, s)


def _normalize_fqid(s):
    """Normalize author FQID for comparison."""
    if not s:
        return ""
    s = str(s).strip().rstrip("/")
    if s.startswith("http://"):
        s = "https" + s[4:]
    return s

def fetch_remote_public_entries(following_remote_fqids=None, friends_remote_fqids=None, requested_by_fqid=None):
    """
    Fetch public entries from IncomingNode nodes.
    - following_remote_fqids: also include UNLISTED from these authors.
    - friends_remote_fqids: also include FRIENDS from these authors (mutual follow).
    - requested_by_fqid: passed as X-Requested-By header so remote can include FRIENDS.
    Returns list of SimpleNamespace objects compatible with stream display.
    """
    following_remote_fqids = following_remote_fqids or []
    friends_remote_fqids = friends_remote_fqids or []
    following_normalized = {_normalize_fqid(f) for f in following_remote_fqids}
    friends_normalized = {_normalize_fqid(f) for f in friends_remote_fqids}

    all_entries = []
    seen_ids = set()

    for node in IncomingNode.objects.all():
        base = node.url.rstrip("/")
        if not base:
            continue

        # Use IncomingNode credentials because we are fetching from THEM
        auth = (node.username, node.password)

        try:
            resp = requests.get(
                f"{base}/api/authors/",
                auth=auth,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            authors = data.get("authors") or []
            if not isinstance(authors, list):
                continue

            for author in authors:
                if not isinstance(author, dict):
                    continue
                author_id_raw = author.get("id")
                if not author_id_raw:
                    continue
                author_id_str = str(author_id_raw).strip().rstrip("/")
                if "/api/authors/" in author_id_str:
                    match = re.search(r"/api/authors/([^/]+)/?", author_id_str)
                    author_num_id = match.group(1) if match else author_id_str
                    node_base = author_id_str.split("/api/authors/")[0]
                else:
                    author_num_id = author_id_str
                    node_base = base

                author_fqid = _normalize_fqid(author_id_str if author_id_str.startswith("http") else f"{node_base.rstrip('/')}/api/authors/{author_num_id}")
                include_unlisted = author_fqid in following_normalized
                include_friends = author_fqid in friends_normalized

                entries_url = f"{node_base}/api/authors/{author_num_id}/entries/"
                headers = {"X-Requested-By": requested_by_fqid} if (include_friends and requested_by_fqid) else {}
                try:
                    entry_resp = requests.get(
                        entries_url,
                        headers=headers,
                        auth=auth,
                        timeout=10,
                    )
                    if entry_resp.status_code != 200:
                        continue
                    entry_data = entry_resp.json()
                    items = entry_data.get("src") or []
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        vis = str(item.get("visibility", "")).upper()
                        if vis == "PUBLIC":
                            pass
                        elif vis == "UNLISTED" and include_unlisted:
                            pass
                        elif vis == "FRIENDS" and include_friends:
                            pass
                        else:
                            continue
                        eid_raw = item.get("id") or ""
                        eid = _resolve_entry_fqid(node_base, author_num_id, eid_raw)
                        if not eid or eid in seen_ids:
                            continue
                        seen_ids.add(eid)

                        author_data = item.get("author") or author
                        likes_obj = item.get("likes") or {}
                        comments_obj = item.get("comments") or {}
                        like_count = likes_obj.get("count", 0) if isinstance(likes_obj, dict) else 0
                        comment_count = comments_obj.get("count", 0) if isinstance(comments_obj, dict) else 0

                        web_raw = item.get("web") or eid_raw or eid
                        remote_web = _absolute_remote_url(node_base, str(web_raw))

                        entry = SimpleNamespace(
                            id=eid,
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            content=item.get("content", ""),
                            contentType=item.get("contentType", "text/plain"),
                            visibility=vis,
                            published=item.get("published", ""),
                            author=SimpleNamespace(
                                id=author_data.get("id", ""),
                                username=author_data.get("displayName") or author_data.get("username", "Remote"),
                            ),
                            is_remote=True,
                            remote_web=remote_web,
                            like_count=like_count,
                            comment_count=comment_count,
                            liked_by_user=False,
                        )
                        all_entries.append(entry)
                except (requests.RequestException, ValueError, KeyError):
                    continue
        except (requests.RequestException, ValueError):
            continue

    return all_entries

def _inbox_url_for_author_fqid(author_fqid: str) -> str:
    """
    Turn a remote author FQID to that author's inbox URL.
    """
    return f"{author_fqid.rstrip('/')}/inbox"

def _credentials_for_remote_author(author_fqid: str):
    """
    Find matching IncomingNode credentials based on the remote node base URL.
    These are the credentials our node uses to authenticate to that remote node.
    """
    author_fqid = _normalize_fqid(author_fqid)

    for node in IncomingNode.objects.all():
        base = (node.url or "").strip().rstrip("/")
        if not base:
            continue
        if author_fqid.startswith(base):
            return (node.username, node.password)

    return None

def get_remote_entry_recipients(author, visibility: str):
    """
    PUBLIC / UNLISTED -> remote followers + remote friends
    FRIENDS -> remote friends only
    DELETED is handled separately from delivery records
    """
    # Fetch all remote following relationships
    remote_followers = {
        _normalize_fqid(x) for x in RemoteFollower.objects.filter(target=author).values_list("actor_fqid", flat=True)
    }
    remote_following = {
        _normalize_fqid(x) for x in RemoteFollow.objects.filter(follower=author).values_list("followed_fqid", flat=True)
    }

    # Intersect two sets to find friends (mutual following)
    remote_friends = remote_followers & remote_following

    # Fetch recipients by different visibilities
    if visibility in {"PUBLIC", "UNLISTED"}:
        return sorted(remote_followers | remote_friends)
    if visibility == "FRIENDS":
        return sorted(remote_friends)
    # If none of the above visibilities, no recipients (DELETED)
    return []


def _post_entry_to_single_remote(entry, request, recipient_fqid: str) -> bool:
    """
    Perform the action of POST request to an outgoing node.
    Check success/failuree by response.
    """
    # Normalize the recipient's FQID and inbox/
    recipient_fqid = _normalize_fqid(recipient_fqid)
    inbox_url = _inbox_url_for_author_fqid(recipient_fqid)

    # Serialize the local entry as unified API Entry Object
    payload = EntrySerializer(entry, context={"request": request}).data
    payload["type"] = "entry"

    # Find credentials for the corresponding outgoing node
    auth = _credentials_for_remote_author(recipient_fqid)
    # Set up request headers (json)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    try:
        # POST
        response = requests.post(
            inbox_url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=10,
        )
        # Check status from the response
        if response.status_code in {200, 201, 202}:
            return True # Success

        # Else Failure and log the failure info
        logger.warning(
            "Entry federation failed entry=%s recipient=%s status=%s body=%s",
            entry.id,
            recipient_fqid,
            response.status_code,
            response.text[:300],
        )
        return False

    except requests.RequestException as exc:
        # Else Failure and log the failure info
        logger.warning(
            "Entry federation request error entry=%s recipient=%s error=%s",
            entry.id,
            recipient_fqid,
            exc,
        )
        return False

# THINKING: any retry model needed? Currently only log failures
def federate_entry_create_or_update(entry, request):
    """
    Send the current entry to all currently eligible remote recipients.
    Also record successful deliveries.
    """
    recipients = get_remote_entry_recipients(entry.author, entry.visibility)

    for recipient_fqid in recipients:
        is_success = _post_entry_to_single_remote(entry, request, recipient_fqid)
        if is_success:
            # Record the corresponding delivery relation
            EntryDelivery.objects.get_or_create(
                entry=entry,
                recipient_fqid=recipient_fqid,
            )

def federate_entry_deleted(entry, request):
    """
    Send deleted-state entry only to recipients that received it before.
    """
    # Track all recipients from previous deliveries relations
    previous_recipients = list(
        entry.deliveries.values_list("recipient_fqid", flat=True)
    )

    for recipient_fqid in previous_recipients:
        _post_entry_to_single_remote(entry, request, recipient_fqid)