# Remote Author Follow — Implementation Guide

## Overview

This node supports full follow relationships with remote authors across different servers. A local author can follow remote authors, and remote authors can follow local authors. Follow relationships use the ActivityPub-style inbox protocol: **Follow** requests are sent to the remote author's inbox, and **Accept** (or rejection) is returned via the requester's inbox.

---

## User Stories Supported

- **Follow remote authors:** Follow authors on other nodes from their profile or via FQID.
- **Approve/deny remote follow requests:** Remote follow requests appear in Follow Requests with Approve/Deny actions.
- **Unfollow remote authors:** Stop following via profile or Connections page.
- **Remove remote followers:** Revoke a remote author's follow on you.
- **Remote friends (mutual follow):** Authors who follow each other are treated as friends for visibility (e.g. FRIENDS entries).
- **Stream integration:** PUBLIC/UNLISTED entries from remote following, FRIENDS entries from remote friends.
- **Entry delivery (US #11):** Entries are sent to remote followers and remote friends according to visibility rules.

---

## Data Models (`core/models.py`)

| Model | Purpose |
|-------|---------|
| **RemoteFollow** | Local author following a remote author. `follower` (local) → `followed_fqid` (remote author URL)|
| **RemoteFollowRequest** | Pending follow request from a remote actor. `actor_fqid`, `actor_display_name`, `target` (local author). |
| **RemoteFollower** | Approved remote follower. `actor_fqid` follows `target` (local author). |

**Friends logic:** A friend = mutual follow. We follow them (RemoteFollow) and they follow us (RemoteFollower) for the same FQID pair.

---

## Follow Flows

### 1. Local Author Follows Remote Author

1. User clicks **Follow** on a remote profile (`/user/<fqid>/follow/`)
2. `follow_remote_author` builds our actor info and POSTs a `Follow` object to `{remote_author_fqid}/inbox`.
3. On success (2xx), creates `RemoteFollow` locally.
4. Remote node may approve or deny; if they approve, they POST `Accept` to our inbox.
5. Our `_inbox_handle_accept` creates/updates `RemoteFollow` so the requester's Connections reflects the approval.

### 2. Remote Author Follows Local Author

1. Remote node POSTs a `Follow` to our unified inbox (`/api/authors/{id}/inbox`).
2. `_inbox_handle_follow` creates `RemoteFollowRequest`.
3. Request appears in Follow Requests; user Approve/Deny.
4. On **Approve**: `approve_remote_follow` creates `RemoteFollower` and `_send_accept_to_requester` POSTs `Accept` to remote actor's inbox.
5. On **Deny**: `deny_remote_follow` deletes the request. No Accept sent.

### 3. Unfollow / Remove Follower

- **Unfollow**: `unfollow_remote_author` deletes `RemoteFollow`. If they were a friend, they move to Remote Followers only.
- **Remove follower**: `remove_remote_follower` deletes `RemoteFollower`.
  

---

## Inbox Payloads

**Follow (we receive from remote):**
```json
{
  "type": "follow",
  "actor": {
    "type": "author",
    "id": "https://other-node.com/api/authors/uuid-or-id",
    "displayName": "Remote Author"
  },
  "object": { "type": "author", "id": "https://our-node.com/api/authors/123" }
}
