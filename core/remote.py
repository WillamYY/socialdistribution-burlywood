"""
Fetch remote public entries from IncomingNode nodes.
Uses same approach as RemoteProfileDisplay - authors from /api/authors/, entries from /api/authors/{id}/entries/
"""
import json
import re
import requests
from types import SimpleNamespace


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


def fetch_remote_public_entries():
    """
    Fetch all public entries from IncomingNode nodes.
    Returns list of SimpleNamespace objects compatible with stream display.
    """
    from core.models import IncomingNode

    all_entries = []
    seen_ids = set()

    for node in IncomingNode.objects.all():
        base = node.url.rstrip("/")
        if not base:
            continue
        try:
            resp = requests.get(f"{base}/api/authors/", timeout=10)
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

                entries_url = f"{node_base}/api/authors/{author_num_id}/entries/"
                try:
                    entry_resp = requests.get(entries_url, timeout=10)
                    if entry_resp.status_code != 200:
                        continue
                    entry_data = entry_resp.json()
                    items = entry_data.get("src") or []
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        if str(item.get("visibility", "")).upper() != "PUBLIC":
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
                            visibility="PUBLIC",
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
