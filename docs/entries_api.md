# Entries and Image API Documentation

This document covers the API implementation and expected behavior for **Entries, Markdown, and Image** user stories, referencing GitHub issues. The following content in this document is generated via the generative AI: Gemini 3 Pro, Google, 2026-03-01, https://gemini.google.com/u/0/app/48a83dd17d81fcf7?pageId=none

### User Stories Covered
* **#10**: As an author, I want to make entries.
* **#12**: As an author, I want to edit my entries locally.
* **#16**: As an author, entries I create can be images.
* **#17**: As an author, I want to delete my own entries locally.
* **#18**: As an author, CommonMark entries can link to images.
* **#21**: As an author, I want to be able to use my web-browser to manage/author my entries.
* **#22**: As an author, other authors cannot modify my entries.

---

## Web Interface for Authors (US #21)

### Purpose

To provide a user-friendly, browser-based management system for authors to create, edit, and delete their entries without using technical API tools.

* **Creation (`/app/create-entry/`):** A dedicated form for authoring new posts.
* **Management (`/app/my-entries/`):** A dashboard to view, edit, or delete existing content.
* **Viewing (`/app/stream/`):** A human-readable feed of posts from the author and their friends.

**How it works:** Relies on `request.session['author_id']` to manage state and permissions. It uses Django Templates to render database content into sanitized HTML, automatically handling Markdown.

---

## Get Author Entries (Paginated)

**URL:** `GET /api/authors/{AUTHOR_SERIAL}/entries/`

* **When to use it:** When a client needs to retrieve a feed of recent entries published by a specific author.
* **How to use it:** Send a GET request. You can optionally append `?page=1&size=5` to paginate the results.
* *Unauthenticated:* Returns only `PUBLIC` entries.
* *Authenticated as Author:* Returns all entries.
* *Authenticated as Follower:* Returns `PUBLIC` + `UNLISTED`.
* *Authenticated as Friend:* Returns all entries.


* **Why to use it:** It correctly implements the project's pagination requirements and filters visibility based on the requester's relationship to the author.
* **Why Not to use it:** Do not use this if you are a remote node trying to pull entries. Remote nodes become aware of local entries via the local node pushing to their inbox, not by pulling from this endpoint.

### Response Examples

**Example 1: First page of public entries**

```json
{
    "type": "entries",
    "page_number": 1,
    "size": 5,
    "count": 24,
    "src": [
        {
            "type": "entry",
            "title": "My first plain text post",
            "id": "http://nodeaaaa/api/authors/123/entries/456",
            "web": "http://nodeaaaa/authors/123/entries/456",
            "description": "Just saying hello",
            "contentType": "text/plain",
            "content": "Hello world! This is my first entry.",
            "author": { "type": "author", "id": "http://nodeaaaa/api/authors/123" },
            "comments": { "type": "comments", "count": 0, "src": [] },
            "likes": { "type": "likes", "count": 0, "src": [] },
            "published": "2023-10-25T13:07:04+00:00",
            "visibility": "PUBLIC"
        }
    ]
}

```

---

## Entry Management (Single Entries)

### A. Get Single Entry

**URL 1 (Local):** `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`
**URL 2 (FQID):** `GET /api/entries/{ENTRY_FQID}`

* **When to use it:** To view the full details of a specific entry, including its comments and likes.
* **How to use it:** Send a GET request. For URL 2, the `ENTRY_FQID` must be URL-encoded.
* **Why to use it:** It returns a deeply nested object with all metadata required to render a single post page.
* **Why Not to use it:** If the entry has a `visibility` of `DELETED`, this will return a `404 Not Found`.

### B. Create Entry (Auto-generated ID)

**URL:** `POST /api/authors/{AUTHOR_SERIAL}/entries/`

* **When to use it:** When a local author is creating a brand new post and wants the server to assign it a unique ID.
* **How to use it:** Send a POST request with the entry details in the body. Must be authenticated locally as the author.
* **Why to use it:** Standard way for the frontend to create posts without needing to generate UUIDs client-side.
* **Why Not to use it:** Do not use this if you are a remote node.

### C. Update / Create Entry (Specific ID)

**URL:** `PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`

* **When to use it:** When a local author is editing an existing post, or when a remote node is pushing an entry to a local inbox.
* **How to use it:** Send a PUT request with the full entry object. Must be authenticated locally.
* **Why to use it:** It allows idempotent creation and updating of entries.
* **Why Not to use it:** If the `session['author_id']` doesn't match the `AUTHOR_SERIAL`, you will get a `403 Forbidden` (US #22).

### D. Delete Entry

**URL:** `DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`

* **When to use it:** When an author wants to remove their own entry.
* **How to use it:** Send a DELETE request. Must be authenticated locally.
* **Why to use it:** Performs a soft-delete, changing the visibility to `DELETED` so it no longer appears in feeds.
* **Why Not to use it:** Cannot be used by remote nodes or other authors.

### Request / Response Examples

**Example 1: POST Request to create an entry**
*(Note: Fields like `comments` and `likes` are omitted in the request because they don't exist yet).*

```json
{
    "title": "Look at this cool image",
    "description": "A picture I took today",
    "contentType": "image/jpeg;base64",
    "content": "/9j/4AAQSkZJRgABAQEASABIAAD...",
    "visibility": "FRIENDS"
}

```

**Example 2: GET Response for an Entry**

```json
{
    "type": "entry",
    "title": "Markdown test",
    "id": "http://nodeaaaa/api/authors/123/entries/789",
    "web": "http://nodeaaaa/authors/123/entries/789",
    "description": "Testing markdown features",
    "contentType": "text/markdown",
    "content": "**Bold text** and *italic*",
    "author": {
        "type": "author",
        "id": "http://nodeaaaa/api/authors/123",
        "host": "http://nodeaaaa/api/",
        "displayName": "John Doe",
        "web": "http://nodeaaaa/authors/123",
        "github": "http://github.com/johndoe",
        "profileImage": "https://i.imgur.com/pic.jpg"
    },
    "comments": {
        "type": "comments",
        "web": "http://nodeaaaa/authors/123/entries/789",
        "id": "http://nodeaaaa/api/authors/123/entries/789/comments",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "http://nodeaaaa/authors/123/entries/789/likes",
        "id": "http://nodeaaaa/api/authors/123/entries/789/likes",
        "page_number": 1,
        "size": 50,
        "count": 0,
        "src": []
    },
    "published": "2023-11-01T10:00:00+00:00",
    "visibility": "PUBLIC"
}

```

---

## Image Proxy API (US #16, #18)

**URL 1:** `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image`
**URL 2:** `GET /api/entries/{ENTRY_FQID}/image`

* **When to use it:** Use this to render an image entry directly inside an HTML `<img>` tag, or to embed images within a CommonMark entry.
* **How to use it:** Place this URL in the `src` attribute of an image tag. It decodes the base64 content on the fly.
* **Why to use it:** It returns raw binary data with the correct `Content-Type` header (e.g., `image/png`). It automates base64 decoding so the frontend client doesn't have to parse JSON just to display a picture.
* **Why Not to use it:** Do not use this endpoint if the target entry has a `contentType` of `text/plain` or `text/markdown`. It will return a `404 Not Found`.

---

## JSON Field Dictionary

### Entries Array (Pagination Object)

| Field | Type | Example | Purpose / When to use |
| --- | --- | --- | --- |
| `type` | `string` | `"entries"` | Identifies the object type. Always present in response. |
| `page_number` | `integer` | `1` | The current page index. Useful for frontend pagination tracking. |
| `size` | `integer` | `5` | Number of items in the current response. |
| `count` | `integer` | `24` | Total number of entries available for this query. |
| `src` | `array` | `[...]` | The actual list of `Entry` objects. |

### Entry Object (Request & Response)

| Field | Type | Example | Purpose / When to use |
| --- | --- | --- | --- |
| `type` | `string` | `"entry"` | Identifies object type. Present in Response. |
| `title` | `string` | `"My Post"` | The title shown to users. Sent in Request, returned in Response. |
| `id` | `string` | `"http://node/api/..."` | The exact API URL of the entry. Autogenerated on POST, required on PUT. |
| `web` | `string` | `"http://node/authors/..."` | URL of the user-facing HTML page for this entry. Response only. |
| `description` | `string` | `"A brief summary"` | Short description. Sent in Request, returned in Response. |
| `contentType` | `string` | `"text/markdown"` | MIME type (`text/plain`, `text/markdown`, `image/png;base64`, etc.). Determines how frontend renders the `content`. |
| `content` | `string` | `"**Hello**"` | The raw text, markdown, or Base64 string. |
| `author` | `object` | `{...}` | Nested Author object detailing who made the post. Response only (inferred from auth on Request). |
| `comments` | `object` | `{...}` | Nested paginated Comments object. First page of comments. Response only. |
| `likes` | `object` | `{...}` | Nested paginated Likes object. First page of likes. Response only. |
| `published` | `string` | `"2015-03-09T13:07:04+00:00"` | ISO 8601 Timestamp. Autogenerated on creation. |
| `visibility` | `string` | `"PUBLIC"` | Access level (`PUBLIC`, `FRIENDS`, `UNLISTED`). Evaluated by the server to restrict viewing. |

---