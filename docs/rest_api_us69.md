# RESTful Interface (User Story #69)

**User Story:** As a node admin, I want a RESTful interface for most operations, so that I can connect to other nodes and allow my users to use alternate clients other than the web frontend.

This document describes the additional REST API endpoints added to support node-to-node communication and alternate clients (e.g. mobile apps, CLI tools).

---

## Followers API

### List Followers

**URL:** `GET /api/authors/{AUTHOR_SERIAL}/followers/`  
**Auth:** Optional (local: session; remote: Basic Auth)

Returns all authors who follow the specified author.

**Response:**
```json
{
  "type": "followers",
  "followers": [
    {
      "type": "author",
      "id": "http://node/api/authors/2",
      "host": "http://node/api/",
      "displayName": "Sandra",
      "github": "",
      "profileImage": null,
      "web": "http://node/app/user/2/"
    }
  ]
}
```

### Check Follower / Accept / Deny

**URL:** `GET|PUT|DELETE /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}/`  
**Auth:** Required for PUT/DELETE (auth_id or session)

- **GET:** Returns 200 with author object if they are a follower, else 404.
- **PUT:** Accept a pending follow request (adds foreign author as follower).
- **DELETE:** Deny follow request or remove follower.

**Note:** `FOREIGN_AUTHOR_FQID` must be URL-encoded (e.g. `http%3A%2F%2Fnode%2Fapi%2Fauthors%2F2`).

---

## Unified Inbox API

**URL:** `POST /api/authors/{AUTHOR_SERIAL}/inbox`  
**Auth:** Remote nodes use HTTP Basic Auth; local uses session.

Accepts objects by `type` and routes accordingly:

| type     | Action                                      |
|----------|---------------------------------------------|
| `like`   | Create like on entry/comment                |
| `follow` | Create follow request (actor → object)      |
| `comment`| Add comment to entry                        |
| `entry`  | Placeholder (inbox storage not yet implemented) |

**Example – Follow:**
```json
{
  "type": "follow",
  "actor": {"type": "author", "id": "http://node1/api/authors/1", ...},
  "object": {"type": "author", "id": "http://node2/api/authors/2", ...}
}
```

**Example – Like:**
```json
{
  "type": "like",
  "author": {"type": "author", "id": "http://node1/api/authors/1", ...},
  "object": "http://node2/api/authors/2/entries/uuid-here"
}
```

**Example – Comment:**
```json
{
  "type": "comment",
  "author": {"type": "author", "id": "http://node1/api/authors/1", ...},
  "entry": "http://node2/api/authors/2/entries/uuid-here",
  "comment": "Nice post!"
}
```

---

## FQID Lookup Endpoints

### Get Author by FQID

**URL:** `GET /api/authors/{AUTHOR_FQID}`  
**Auth:** Optional

Retrieves an author profile by full URL (for remote node lookups).  
Example: `GET /api/authors/http%3A%2F%2Fnode%2Fapi%2Fauthors%2F123`

### Get Entry by FQID

**URL:** `GET /api/entries/{ENTRY_FQID}`  
**Auth:** Required for friends-only entries

Retrieves an entry by full URL.  
Example: `GET /api/entries/http%3A%2F%2Fnode%2Fapi%2Fauthors%2F1%2Fentries%2Fuuid`

### Get Comments by Entry FQID

**URL:** `GET /api/entries/{ENTRY_FQID}/comments/`  
**Auth:** Required for friends-only entries

Returns comments for an entry identified by FQID.

---

## Likes on Comments

**URL:** `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_FQID}/likes/`  
**Auth:** Required for friends-only entries

Returns likes on a specific comment. Supports `page_number` and `size` query params.

---

## Summary

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/authors/{id}/followers/` | GET | List followers |
| `/api/authors/{id}/followers/{fqid}/` | GET, PUT, DELETE | Check/accept/deny follower |
| `/api/authors/{id}/inbox` | POST | Unified inbox (like, follow, comment, entry) |
| `/api/authors/{AUTHOR_FQID}` | GET | Get author by FQID |
| `/api/entries/{ENTRY_FQID}` | GET | Get entry by FQID |
| `/api/entries/{ENTRY_FQID}/comments/` | GET | Get comments by entry FQID |
| `.../comments/{COMMENT_FQID}/likes/` | GET | Get likes on a comment |


## Citation
- For documentation and Tests cases, used genAI for formatting help.
