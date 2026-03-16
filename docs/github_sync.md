# GitHub Activity Sync (User Story #5)

**User Story:** As an author, I want my (new, public) GitHub activity to be automatically turned into public entries, so everyone can see my GitHub activity too.

## Overview

Authors with a GitHub profile URL in their profile can sync their public GitHub activity into the social distribution platform as **public entries**. Synced entries appear in the stream and public feeds for everyone to see.

## How to Use

### 1. Add GitHub URL to Profile

- Go to **Edit Profile** and add your GitHub profile URL (e.g. `https://github.com/yourusername`).

### 2. Automatic Sync (No Action Required)

- **When you view the stream:** GitHub activity for all authors with a GitHub URL is synced automatically (throttled to every 10 seconds). New pushes, stars, issues, etc. show up in the stream without any button click or profile save.
- **When you save your profile** with a GitHub URL: your activity is also synced immediately so new entries appear right away.

### 3. Bulk Sync (Management Command)

Run periodically (e.g. via cron) to sync all authors with GitHub URLs:

```bash
python manage.py sync_github
```

Sync a single author:

```bash
python manage.py sync_github --author-id 1
```

**Cron example** (every hour):

```
0 * * * * cd /path/to/project && .venv/bin/python manage.py sync_github
```

## Supported Event Types

| Event Type | Entry Example |
|------------|---------------|
| PushEvent | "Pushed 3 commit(s) to owner/repo" |
| ForkEvent | "Forked owner/repo" |
| WatchEvent | "Starred owner/repo" |
| CreateEvent | "Created branch main in owner/repo" |
| IssuesEvent | "Opened issue in owner/repo" |
| PullRequestEvent | "Merged pull request in owner/repo" |
| ReleaseEvent | "Published release in owner/repo" |
| PublicEvent | "Made owner/repo public" |

## Duplicate Prevention

Each GitHub event has a unique ID. The system stores `github_event_id` on entries to avoid importing the same event twice.

## Rate Limits

- **Without token:** 60 requests/hour (GitHub API limit).
- **With token:** 5000 requests/hour. Set `GITHUB_TOKEN` environment variable.

## Technical Notes

- Fetches from `GET /users/{username}/events/public`
- GitHub retains events for ~30 days
- Entries are always created with `visibility=PUBLIC`
- Content is rendered as Markdown and sanitized for XSS
