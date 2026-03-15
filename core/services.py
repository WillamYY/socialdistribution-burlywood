"""
Services for core app - GitHub activity sync (User Story #5).
"""
import re

import bleach
import markdown
import requests
from django.conf import settings

from core.models import Author
from entries.models import Entry


def _render_safe_markdown(text):
    """Convert Markdown to HTML and sanitize for XSS."""
    if not text:
        return ""
    html = markdown.markdown(text, extensions=["extra", "codehilite"])
    allowed = ["p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "blockquote",
               "code", "pre", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "a", "img",
               "table", "thead", "tbody", "tr", "th", "td"]
    return bleach.clean(html, tags=allowed, attributes={"a": ["href", "title"], "img": ["src", "alt", "title"]})


def extract_github_username(github_url):
    """
    Extract GitHub username from a profile URL.
    Handles: https://github.com/username, https://github.com/username/, http://github.com/username
    Returns None if URL is invalid or not a GitHub profile URL.
    """
    if not github_url or not github_url.strip():
        return None
    url = github_url.strip().rstrip('/')
    # Match github.com/username (with optional path we ignore)
    match = re.search(r'github\.com/([^/?#]+)', url, re.IGNORECASE)
    return match.group(1) if match else None


def format_github_event_as_entry(event):
    """
    Convert a GitHub API event into (title, description, content) for an Entry.
    Returns None if we don't support this event type.
    """
    event_type = event.get('type')
    payload = event.get('payload', {})
    repo = event.get('repo', {})
    repo_name = repo.get('name', 'unknown')
    repo_url = f"https://github.com/{repo_name}" if repo_name != 'unknown' else ''
    created_at = event.get('created_at', '')

    title = None
    description = ''
    content_parts = [f"**Repository:** [{repo_name}]({repo_url})"]

    if event_type == 'PushEvent':
        commits = payload.get('commits', [])
        size = payload.get('size', len(commits))
        commit_count = max(size, len(commits))  # API sometimes sends size=0
        ref = payload.get('ref', '')
        branch = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
        title = f"Pushed {commit_count} commit(s) to {repo_name}" if commit_count else f"Pushed to {repo_name}"
        description = f"Push to {branch}"
        if commits:
            content_parts.append("\n**Commits:**")
            for c in commits[:5]:  # Show up to 5
                msg = c.get('message', '').split('\n')[0][:80]
                sha = c.get('sha', '')[:7]
                content_parts.append(f"- `{sha}` {msg}")
            if len(commits) > 5:
                content_parts.append(f"- ... and {len(commits) - 5} more")

    elif event_type == 'CreateEvent':
        ref_type = payload.get('ref_type', '')
        ref = payload.get('ref', '')
        title = f"Created {ref_type} in {repo_name}"
        description = f"Created {ref_type} {ref}" if ref else f"Created {ref_type}"
        content_parts.append(f"\n**{ref_type.title()}:** {ref}" if ref else '')

    elif event_type == 'ForkEvent':
        forkee = payload.get('forkee', {})
        full_name = forkee.get('full_name', repo_name)
        title = f"Forked {repo_name}"
        description = f"Forked to {full_name}"
        content_parts.append(f"\n**Fork:** {full_name}")

    elif event_type == 'IssuesEvent':
        action = payload.get('action', '')
        issue = payload.get('issue', {})
        issue_title = issue.get('title', '')
        issue_url = issue.get('html_url', '')
        title = f"{action.capitalize()} issue in {repo_name}"
        description = issue_title[:100]
        content_parts.append(f"\n**Issue:** [{issue_title}]({issue_url})")

    elif event_type == 'PullRequestEvent':
        action = payload.get('action', '')
        pr = payload.get('pull_request', {})
        pr_title = pr.get('title', '')
        pr_url = pr.get('html_url', '')
        title = f"{action.capitalize()} pull request in {repo_name}"
        description = pr_title[:100]
        content_parts.append(f"\n**PR:** [{pr_title}]({pr_url})")

    elif event_type == 'WatchEvent':
        # Starred a repo
        title = f"Starred {repo_name}"
        description = f"Starred {repo_name}"
        content_parts.append(f"\n**Repository:** [{repo_name}]({repo_url})")

    elif event_type == 'ReleaseEvent':
        action = payload.get('action', '')
        release = payload.get('release', {})
        tag = release.get('tag_name', '')
        name = release.get('name') or tag
        title = f"{action.capitalize()} release in {repo_name}"
        description = name or tag
        content_parts.append(f"\n**Release:** {name} ({tag})")

    elif event_type == 'PublicEvent':
        title = f"Made {repo_name} public"
        description = f"Repository {repo_name} is now public"

    else:
        # Unsupported event type
        return None

    content_raw = '\n'.join(p for p in content_parts if p)
    content_html = _render_safe_markdown(content_raw)
    return {
        'title': title,
        'description': description,
        'content': content_html,
        'content_raw': content_raw,
        'created_at': created_at,
    }


def fetch_github_events(username, token=None, per_page=30):
    """
    Fetch public events for a GitHub user.
    Returns list of events or None on error.
    """
    token = token or getattr(settings, 'GITHUB_TOKEN', '') or ''
    url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        resp = requests.get(url, headers=headers, params={'per_page': per_page}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 304:
            return []
        return None
    except requests.RequestException:
        return None


def sync_author_github_activity(author):
    """
    Fetch GitHub public events for an author and create PUBLIC entries for new ones.
    Uses github_event_id to avoid duplicates.
    Returns (created_count, error_message).
    """
    username = extract_github_username(author.github)
    if not username:
        return 0, "No valid GitHub URL in profile"

    events = fetch_github_events(username)
    if events is None:
        return 0, "Failed to fetch GitHub events (check username or rate limit)"

    created = 0
    for event in events:
        event_id = event.get('id')
        if not event_id:
            continue
        if Entry.objects.filter(github_event_id=event_id).exists():
            continue
        formatted = format_github_event_as_entry(event)
        if not formatted:
            continue
        try:
            Entry.objects.create(
                author=author,
                title=formatted['title'],
                description=formatted['description'],
                contentType='text/markdown',
                content=formatted['content'],
                content_raw=formatted.get('content_raw', formatted['content']),
                visibility='PUBLIC',
                github_event_id=event_id,
            )
            created += 1
        except Exception:
            pass  # Skip on duplicate or other DB error
    return created, None


def sync_all_authors_github():
    """
    Sync GitHub activity for all authors that have a GitHub URL.
    Returns dict: {author_id: (created_count, error)}.
    """
    authors = Author.objects.exclude(github='').exclude(github__isnull=True)
    results = {}
    for author in authors:
        created, err = sync_author_github_activity(author)
        results[author.id] = (created, err)
    return results


def maybe_sync_github_for_stream():
    """
    Run sync for all authors with GitHub URLs if enough time has passed since last run.
    Called when the stream is viewed so new GitHub activity shows up automatically.
    Uses cache to throttle (default: once per GITHUB_SYNC_INTERVAL seconds).
    """
    from django.core.cache import cache
    cache_key = 'github_stream_sync_last_run'
    interval = getattr(settings, 'GITHUB_SYNC_INTERVAL', 300)
    if cache.get(cache_key):
        return
    cache.set(cache_key, True, timeout=interval)
    sync_all_authors_github()
