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
from entries.models import Entry
from interactions.models import Like

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
    requested_by_fqid_norm = _normalize_fqid(requested_by_fqid) if requested_by_fqid else ""

    all_entries = []
    seen_ids = set()

    for node in IncomingNode.objects.all():
        base = (node.url or "").rstrip("/")
        if not base:
            continue

        # Use IncomingNode credentials because we are fetching from THEM
        auth = (node.username, node.password)
        logger.info("STREAM FETCH authors node=%s username=%s", base, node.username)

        try:
            resp = requests.get(
                f"{base}/api/authors/",
                auth=auth,
                headers={"Accept": "application/json"},
                timeout=10,
            )
            logger.info(
                "STREAM FETCH authors response node=%s status=%s body=%s",
                base,
                resp.status_code,
                resp.text[:200] if resp.text else "",
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            authors = data.get("authors") or data.get("src") or []
            if not isinstance(authors, list):
                logger.warning("STREAM FETCH authors bad-shape node=%s data=%s", base, str(data)[:200])
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
                print(author_fqid)
                entries_url = f"{node_base}/api/authors/{author_num_id}/entries/"
                headers = {"Accept": "application/json"}
                if include_friends and requested_by_fqid:
                    headers["X-Requested-By"] = requested_by_fqid

                try:
                    entry_resp = requests.get(
                        entries_url,
                        headers=headers,
                        auth=auth,
                        timeout=10,
                    )
                    logger.info(
                        "STREAM FETCH entries author=%s url=%s status=%s body=%s",
                        author_fqid,
                        entries_url,
                        entry_resp.status_code,
                        entry_resp.text[:200] if entry_resp.text else "",
                    )
                    if entry_resp.status_code != 200:
                        continue
                    entry_data = entry_resp.json()
                    items = entry_data.get("src") or entry_data.get("entries") or []
                    if not isinstance(items, list):
                        logger.warning(
                            "STREAM FETCH entries bad-shape author=%s data=%s",
                            author_fqid,
                            str(entry_data)[:200],
                        )
                        continue

                    added_for_author = 0

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        vis = str(item.get("visibility", "")).upper()
                        if vis == "PUBLIC":
                            pass
                        elif vis == "UNLISTED" and include_unlisted:
                            pass
                        elif vis == "FRIENDS" and include_friends:
                            print("FRIEND YOU CAN SEE")
                            pass
                        else:
                            print("TESTING",)
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

                        # If we're logged in, reflect local like state in `liked_by_user`.
                        # This allows the Stream UI to turn the heart "red/filled" for remote entries.
                        # Normalize for comparisons (treat http/https as equivalent).
                        object_url_norm = _normalize_fqid(eid)
                        liked_by_user = False
                        if requested_by_fqid_norm:
                            liked_by_user = Like.objects.filter(
                                author=requested_by_fqid_norm,
                                object=object_url_norm,
                            ).exists()

                        entry = SimpleNamespace(
                            id=eid,
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            content=item.get("content", ""),
                            contentType=item.get("contentType", "text/plain"),
                            visibility=vis,
                            image = item.get("image",None),
                            published=item.get("published", ""),
                            author=SimpleNamespace(
                                id=author_data.get("id", ""),
                                username=author_data.get("displayName") or author_data.get("username", "Remote"),
                            ),
                            is_remote=True,
                            remote_web=remote_web,
                            like_count=like_count,
                            comment_count=comment_count,
                            liked_by_user=liked_by_user,
                        )
                        all_entries.append(entry)
                        added_for_author += 1

                    logger.info(
                        "STREAM FETCH entries accepted author=%s count=%s",
                        author_fqid,
                        added_for_author,
                    )

                except (requests.RequestException, ValueError, KeyError) as exc:
                    logger.warning(
                        "STREAM FETCH entries error author=%s url=%s error=%s",
                        author_fqid,
                        entries_url,
                        exc,
                    )
                    continue
                    
        except (requests.RequestException, ValueError) as exc:
            logger.warning("STREAM FETCH authors error node=%s error=%s", base, exc)
            continue

    logger.info("STREAM FETCH total remote entries=%s", len(all_entries))
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
    authorfqid = author.host + "/authors/" + str(author.id)

    true_remote_following = set()
    for following in remote_following:
        try:
            remote_host = following[:following.index("/api")] + "/"
            credentials = IncomingNode.objects.get(url = remote_host)
            response = requests.get(
                f"{following}/followers/{authorfqid}",
                headers={"Accept": "application/json"},
                auth=(credentials.username, credentials.password),
                timeout=10
            )
            if response.status_code < 400:
                true_remote_following.add(following)
        except:
            pass
    # Intersect two sets to find friends (mutual following)
    # remote_friends = remote_followers & remote_following
    remote_friends = remote_followers & true_remote_following

    # Fetch recipients by different visibilities
    if visibility in {"PUBLIC", "UNLISTED"}:
        return sorted(remote_followers | remote_friends)
    if visibility == "FRIENDS":
        return sorted(remote_friends)
    # If none of the above visibilities, no recipients (DELETED)
    return []

def _build_entry_payload(entry, request, visibility_override=None):
    """
    Helper function to create a clean JSON representation of an entry
    """
    payload = EntrySerializer(entry, context={"request": request}).data
    payload["type"] = "entry"
    if visibility_override is not None:
        payload["visibility"] = visibility_override
    return payload

def _post_payload_to_single_remote(payload, recipient_fqid: str) -> bool:
    """
    Perform the action of POST request to an outgoing node.
    Check success/failuree by response.
    """
    # Normalize the recipient's FQID and inbox/
    recipient_fqid = _normalize_fqid(recipient_fqid)
    inbox_url = _inbox_url_for_author_fqid(recipient_fqid)

    # Find credentials for the corresponding outgoing node
    auth = _credentials_for_remote_author(recipient_fqid)
    # Set up request headers (json)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    try:
        # POST
        print("==============INBOX URL", inbox_url)
        print("==============PAYLOAD", payload)
        response = requests.post(
            inbox_url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=10,
        )
        print(response.content, response.status_code)

        # Check status from the response
        if response.status_code in {200, 201, 202}:
            return True # Success

        # Else Failure and log the failure info
        logger.warning(
            "Entry federation failed recipient=%s status=%s body=%s",
            recipient_fqid,
            response.status_code,
            response.text[:300],
        )
        return False

    except requests.RequestException as exc:
        # Else Failure and log the failure info
        logger.warning(
            "Entry federation request error recipient=%s error=%s",
            recipient_fqid,
            exc,
        )
        return False

def _post_entry_to_single_remote(entry, request, recipient_fqid: str, visibility_override=None) -> bool:
    # Serialize the local entry as unified API Entry Object
    payload = _build_entry_payload(entry, request, visibility_override=visibility_override)
    return _post_payload_to_single_remote(payload, recipient_fqid)

# THINKING: any retry model needed? Currently only log failures
def federate_entry_create_or_update(entry, request):
    """
    Send the current entry to all currently eligible remote recipients.
    Also record successful deliveries.
    """
    # Filter current recipients by current following/follwer list.
    current_recipients = {
        _normalize_fqid(x) for x in get_remote_entry_recipients(entry.author, entry.visibility)
    }
    # Track all recipients from EntryDelivery table in DB
    previous_recipients = {
        _normalize_fqid(x) for x in entry.deliveries.values_list("recipient_fqid", flat=True)
    }
    
    current_payload = _build_entry_payload(entry, request)

    # Send/update to everyone who should currently have it
    for recipient_fqid in current_recipients:
        if _post_payload_to_single_remote(current_payload, recipient_fqid):
            EntryDelivery.objects.get_or_create(
                entry=entry,
                recipient_fqid=recipient_fqid,
            )
    
    # Retract from nodes that had it before but should not have it now
    removed_recipients = previous_recipients - current_recipients
    if removed_recipients:
        deleted_payload = dict(current_payload)
        # Let "DELETED" as a hide flag
        deleted_payload["visibility"] = "DELETED"

        for recipient_fqid in removed_recipients:
            _post_payload_to_single_remote(deleted_payload, recipient_fqid)

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

def backfill_entries_to_remote_recipient(author, remote_recipient_fqid, relation_type, request):
    """
    Send previous visible entries to new recipient's inbox.
    """
    entries = Entry.objects.filter(author=author).exclude(visibility="DELETED").order_by("published")

    for entry in entries:
        visibility = entry.visibility

        if visibility == "PUBLIC":
            allowed = True
        elif visibility == "UNLISTED":
            allowed = relation_type in {"follower", "friend"}
        elif visibility == "FRIENDS":
            allowed = relation_type == "friend"
        else:
            allowed = False

        if not allowed:
            continue

        if _post_entry_to_single_remote(entry, request, remote_recipient_fqid):
            EntryDelivery.objects.get_or_create(
                entry=entry,
                recipient_fqid=_normalize_fqid(remote_recipient_fqid),
            )
