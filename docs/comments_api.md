# Comments API Documentation

This document describes the API endpoints related to comments on entries, including comment creation, retrieval, and visibility rules.

These endpoints support the following user stories:

- #57 As an author, I want to comment on entries I can access.
- #62 As an author, comments on my friends-only entries are visible only to my friends and the comment's author.
- #59 As an author, I want to like comments that I can access.

---

# Object Schemas

## Comment Object

Represents a single comment made on an entry.

| Field | Type | Description |
|------|------|-------------|
| type | string | Always `"comment"` |
| id | string (URL) | Fully Qualified ID (FQID) of the comment |
| author | object | Author object describing the commenter |
| comment | string | Text content of the comment |
| contentType | string | Content format (`text/plain` or `text/markdown`) |
| published | datetime | Timestamp when the comment was created |
| object | string (URL) | FQID of the entry the comment belongs to |

---

## Author Object

Represents the author who created the comment.

| Field | Type | Description |
|------|------|-------------|
| type | string | `"author"` |
| id | string (URL) | FQID of the author |
| host | string (URL) | Host node of the author |
| displayName | string | Author display name |
| github | string | GitHub profile URL |
| profileImage | string | Profile image URL |
| web | string | Author profile webpage |

Example:

```json
{
  "type": "author",
  "id": "http://127.0.0.1:8000/api/authors/1",
  "host": "http://127.0.0.1:8000/api/",
  "displayName": "displayName",
  "github": "",
  "profileImage": null,
  "web": "http://127.0.0.1:8000/authors/1"
}
```

---

## Comments Object

Represents a paginated collection of comments.

| Field | Type | Description |
|------|------|-------------|
| type | string | `"comments"` |
| id | string | Endpoint used to retrieve the comments |
| page_number | integer | Current page number |
| size | integer | Number of comments per page |
| count | integer | Total number of comments |
| src | array | List of Comment objects |

---

# API Endpoints

## Create Comment

Creates a comment on a specific entry.

### Endpoint

```
POST /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments
```

### Description

Creates a comment on an entry if the requesting author has permission to access the entry.

---

### Request Body Example

```json
{
  "type": "comment",
  "author": {
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/1",
    "displayName": "displayName",
    "github": "",
    "profileImage": ""
  },
  "comment": "Nice post!",
  "contentType": "text/plain"
}
```

---

### Successful Response

**201 Created**

```json
{
  "type": "comment",
  "id": "http://127.0.0.1:8000/comments/4fae7c18",
  "author": {
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/1",
    "displayName": "displayName",
    "github": "",
    "profileImage": ""
  },
  "comment": "Nice post!",
  "contentType": "text/plain",
  "published": "2026-03-01T13:10:07.085666-07:00",
  "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32"
}
```

---

### Status Codes

| Code | Meaning |
|-----|--------|
| 201 | Comment successfully created |
| 400 | Invalid request body |
| 401 | Authentication required |
| 403 | User does not have permission to comment |
| 404 | Entry or author not found |
| 405 | Method not allowed |

---

## Get Comments on Entry

Returns all comments on a specific entry.

### Endpoint

```
GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments
```

### Description

Returns comments associated with the entry.

Comments returned depend on the visibility of the entry and the requesting user's permissions.

---

### Response Example

```json
{
  "type": "comments",
  "id": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32/comments",
  "page_number": 1,
  "size": 5,
  "count": 1,
  "src": [
    {
      "type": "comment",
      "id": "http://127.0.0.1:8000/comments/4fae7c18",
      "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/1",
        "host": "http://127.0.0.1:8000/api/",
        "displayName": "displayName",
        "github": "",
        "profileImage": null,
        "web": "http://127.0.0.1:8000/authors/1"
      },
      "comment": "Nice post!",
      "contentType": "text/plain",
      "published": "2026-03-01T13:10:07.085666-07:00",
      "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32"
    }
  ]
}
```

---

### Status Codes

| Code | Meaning |
|-----|--------|
| 200 | Comments successfully retrieved |
| 403 | Entry is not visible to requester |
| 404 | Entry or author not found |
| 405 | Method not allowed |

---

## Get Comments Using Entry FQID

Allows nodes to retrieve comments using the entry's fully qualified ID.

### Endpoint

```
GET /api/entries/{ENTRY_FQID}/comments
```

### Description

Returns comments associated with the entry identified by the FQID.

This endpoint is used for federated node communication between servers.

The response structure is the same as the **Comments Object**.

---

# Pagination

Comment lists support pagination.

| Parameter | Description |
|----------|-------------|
| page | Page number |
| size | Number of comments per page |

Example request:

```
GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments?page=1&size=5
```

---

# Visibility Rules

Comments follow the visibility rules of the entry they belong to.

| Entry Visibility | Who Can See Comments |
|-----------------|----------------------|
| PUBLIC | Everyone |
| UNLISTED | Anyone with the link |
| FRIENDS | Mutual followers only |
| DELETED | No one |

---

# Notes

Comments reference entries using **Fully Qualified IDs (FQIDs)** to ensure compatibility with federated nodes.

Comment IDs are also stored as FQIDs to guarantee global uniqueness across different nodes.

---

## Comment Federation (Outgoing Node)

### Purpose
To ensure that comments created on a local node can be delivered to remote authors when the target entry belongs to another node.

### How it works
Whenever a local author comments on a **remote entry**, the local node serializes the comment into the standard JSON Comment Object and sends it to the remote author's **Inbox**.

1. **Target Resolution:** The system identifies the remote entry's FQID and the remote author who owns that entry.
2. **Serialization:** The comment is converted into a JSON Comment Object containing:
   - `type: "comment"`
   - `author` as a full Author object
   - `comment`
   - `contentType`
   - `published`
   - `id`
   - `entry` (or `object`, depending on remote compatibility)
3. **Delivery:** The node performs a `POST` request to the remote author's Inbox endpoint.
4. **Authentication:** The request is authenticated using stored node credentials.

```md
### Expected Federation Behavior

| Action | Triggering Operation | Federation Method | Payload |
| :--- | :--- | :--- | :--- |
| **Create Remote Comment** | Local author comments on remote entry | `POST` to Inbox | Full Comment Object |

### Example Outgoing Payload

```json
{
  "type": "comment",
  "author": {
    "type": "author",
    "id": "http://nodeaaaa/api/authors/111",
    "host": "http://nodeaaaa/api/",
    "displayName": "Greg Johnson",
    "github": "http://github.com/gjohnson",
    "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
    "web": "http://nodeaaaa/authors/greg"
  },
  "comment": "Sick Olde English",
  "contentType": "text/markdown",
  "published": "2015-03-09T13:07:04+00:00",
  "id": "http://nodeaaaa/api/authors/111/commented/130",
  "entry": "http://nodebbbb/api/authors/222/entries/249"
}

```md
---

# Citation

Some documentation text and formatting improvements were generated with assistance from **ChatGPT (OpenAI)**.

OpenAI. (2026). *ChatGPT*. https://chatgpt.com