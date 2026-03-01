# Comments & Likes API Documentation

This document covers the API implementation and expected behavior for the **Comments and Likes** user stories, referencing GitHub issues.

### User Stories Covered
* **#58**: As an author, I want to like entries that I can access, so I can show my appreciation.
* **#59**: As an author, I want to like comments that I can access, so I can show my appreciation.
* **#60**: As an author, when someone sends me a public entry I want to see the likes, so I can tell if it's good or not.
* **#62**: As an author, comments on my friends-only entries are visible only to my friends and the comment's author.

---

## Get Comments on an Entry
**URL:** `GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments/`

### When to use it
* Use this to retrieve all comments associated with a specific entry.

### How to use it
* The `{AUTHOR_ID}` and `{ENTRY_ID}` must match an existing entry on the node.
* Returns comments sorted by most recent first.

### Why/Why Not to use it
* **Why**: Provides a structured comment list compatible with federation and other nodes.
* **Why Not**: Will return `404` if the entry does not exist.

### Response JSON Fields
| Field | Type | Example | Purpose |
| :--- | :--- | :--- | :--- |
| `type` | `string` | `"comments"` | Identifies the object type. |
| `id` | `string` | `"http://.../comments"` | URL of this comments collection. |
| `page` | `integer` | `1` | Current page index. |
| `size` | `integer` | `5` | Number of comments returned. |
| `count` | `integer` | `12` | Total comments available. |
| `src` | `array` | `[...]` | List of Comment objects. |

---

## Comment Object Fields

| Field | Type | Example | Purpose |
| :--- | :--- | :--- | :--- |
| `type` | `string` | `"comment"` | Identifies object as a comment. |
| `id` | `string` | `"http://.../comments/uuid"` | Fully qualified ID for federation. |
| `author` | `string` | `"http://.../authors/1"` | URL of the comment author. |
| `comment` | `string` | `"Nice post!"` | The comment content. |
| `contentType` | `string` | `"text/plain"` | MIME type of the comment. |
| `published` | `string` | `"2026-03-01T12:00:00Z"` | Timestamp of creation. |

---

## Add Comment to Entry
**URL:** `POST /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments/add/`

### When to use it
* Use this to create a new comment on an entry the author can access.

### How to use it
Request JSON must include:

```json
{
  "author": "http://node/api/authors/1",
  "comment": "Nice post!",
  "contentType": "text/plain"
}