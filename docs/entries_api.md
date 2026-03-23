# Entries and Image API Documentation

This document covers the API implementation and expected behavior for **Entries and Visibility** user stories, referencing GitHub issues. The following content in this document is mainly generated with the help of the generative AI: Gemini 3 Flash, Google, 2026-03-23, https://gemini.google.com/u/0/app/48a83dd17d81fcf7?pageId=none

### User Stories Covered
* **#6**: As an author, I want my profile page to show my public entries (most recent first), so they can decide if they want to follow me.
* **#10**: As an author, I want to make entries.
* **#12**: As an author, I want to edit my entries locally.
* **#14**: As an author, entries I make can be in simple plain text.
* **#15**: As an author, entries I make can be in CommonMark.
* **#16**: As an author, entries I create can be images.
* **#17**: As an author, I want to delete my own entries locally.
* **#18**: As an author, CommonMark entries can link to images.
* **#21**: As an author, I want to be able to use my web-browser to manage/author my entries.
* **#22**: As an author, other authors cannot modify my entries.
* **#34**: As an author, I want to be able to make my entries public, so that everyone can see them.
* **#35**: As an author, I want to be able to make my entries unlisted, so that my followers see them, and anyone with the link can also see them.
* **#36**: As an author, I want to be able to make my entries friends-only.
* **#40**: As an author, I want everyone to be able to see my public and unlisted entries, if they have a link to it.
* **#41**: As an author, I don't want anyone who isn't a friend to be able to see my friends-only entries and images.
* **#42**: As an author, I don't want anyone except the node admin to see my deleted entries.
* **#44**: As a reader, I can get a link to a public or unlisted entry, so I can send it to my friends over email, discord, slack, etc.
* **#46**: As an author, I should be able to browse the public entries of everyone, so that I can see what's going on beyond authors I follow. Note: this should include all local public entries and all public entries received in any inbox.
* **#65**: As a node admin, images can be hosted on my node, so that my users can use them in their CommonMark entries.
* **#78**: As a node admin, I want deleted entries stay in the database and only be removed from the UI and API, so I can see what was deleted.
* **#91**: As an author, entries I create should always be visible to me until they are deleted.
* **#11**: As an author, I want my node to send my entries to my remote followers and friends.
* **#13**: As an author, I want my node to re-send entries I've edited to everywhere they were already sent.
* **#23**: As an author, I want my node to re-send entries I've deleted to everyone they were already sent.
* **#45**: As a node admin, I want to push images to users on other nodes.

---

## Web Interface for Authors (US #21)

### Purpose

To provide a user-friendly, browser-based management system for authors to create, edit, and delete their entries without using technical API tools.

* **Creation (`/app/create-entry/`):** A dedicated form for authoring new posts.
* **Management (`/app/my-entries/`):** A dashboard to view the logged-in author’s entries and access edit or delete actions.
* **Editing (`/app/edit/{ENTRY_ID}/`):** A browser form that allows the owner of an entry to update its title, description, content, visibility, and image content.
* **Deletion (`/app/delete/{ENTRY_ID}/`):** A browser action that soft-deletes an entry.
* **Viewing (`/app/author/{AUTHOR_ID}/entries/` and `/app/entry/{ENTRY_ID}/`):** Human-readable pages for browsing an author’s entries or viewing a single entry.

**How it works:** Relies on `request.session['author_id']` to manage state and permissions. It uses Django templates to render database content into sanitized HTML, including Markdown rendering and image embedding.

**Behavior supporting US #21:**
A local author can create, edit, and delete entries entirely through browser forms. These pages are session-protected, so only the entry owner can edit or delete their own content. This allows authoring without needing to manually use JSON APIs.

---

## Entry Visibility Rules

The system currently supports these visibility values:

* **`PUBLIC`** — visible to everyone.
* **`UNLISTED`** — not shown in general public browsing, but visible to followers in author-entry lists and to anyone who has the direct link.
* **`FRIENDS`** — visible only to the entry owner and mutual followers ("friends").
* **`DELETED`** — soft-deleted; remains in the database but is removed from normal UI and API responses.

This supports:

* **US #34**
* **US #35**
* **US #36**
* **US #40**
* **US #41**
* **US #42**
* **US #78**
* **US #91**

### Visibility Behavior Details

* **PUBLIC**

  * Appears in author-entry lists.
  * Appears in the public browse endpoint.
  * Can be opened directly by link.
  * Supports profile-page browsing by strangers.

* **UNLISTED**

  * Does not appear in the public browse endpoint.
  * Appears in author-entry lists for the owner and followers.
  * Can be opened directly by anyone who has the link.
  * Supports the “share by URL” requirement.

* **FRIENDS**

  * Appears only to the owner and mutual followers.
  * Does not appear to strangers or simple followers.
  * Direct-link access is still restricted by friendship rules.

* **DELETED**

  * Does not appear in author-entry lists.
  * Does not appear in the public browse endpoint.
  * Single-entry APIs and web pages treat it as unavailable.
  * Still remains in the database as a soft-deleted row.

---

## Get Author Entries (Paginated)

**URL:** `GET /api/authors/{AUTHOR_SERIAL}/entries/`
**Relevant User Stories:** #6, #35, #36, #41, #91

* **When to use it:** When a client needs to retrieve a feed of recent entries published by a specific author.
* **How to use it:** Send a GET request. You can optionally append `?page=1&size=5` to paginate the results.

* **Unauthenticated:** Returns only `PUBLIC` entries.

* **Authenticated as Author:** Returns all non-deleted entries created by that author.

* **Authenticated as Follower:** Returns `PUBLIC` + `UNLISTED`.

* **Authenticated as Friend:** Returns `PUBLIC` + `UNLISTED` + `FRIENDS`.

* **Why to use it:** It correctly implements pagination and filters entries based on the requester’s relationship to the author.

* **Why Not to use it:** Do not use this endpoint to retrieve a single entry by direct link. Use the single-entry endpoint instead.

### Story Behavior Notes

**US #6:**
This endpoint supports profile-style entry browsing. When someone visits an author’s entries, they receive only the entries they are allowed to see, and the entries are returned **most recent first**. For strangers, that means public entries only. This helps readers decide whether they want to follow the author.

**US #35:**
Unlisted entries are visible in this list to followers and to the owner, but not to strangers.

**US #36 / #41:**
Friends-only entries appear only for the owner and mutual followers. They are not included for strangers or non-friend followers.

**US #91:**
The owner can always retrieve all of their own non-deleted entries through this endpoint.

### Expected Status Codes

* **`200 OK`**: Successfully retrieved the filtered paginated list of entries.
* **`404 Not Found`**: The target author does not exist.

### Response Example

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
**URL 2 (FQID):** `GET /api/entries/{ENTRY_FQID}/`
**Relevant User Stories:** #40, #41, #44, #91

* **When to use it:** To view the full details of a specific entry, including its comments and likes.
* **How to use it:** Send a GET request. For URL 2, the `ENTRY_FQID` must be URL-encoded.
* **Why to use it:** It returns a single entry object and applies visibility checks based on the requester.

### Direct-link behavior

* **`PUBLIC`** entries are accessible.
* **`UNLISTED`** entries are accessible to anyone with the link.
* **`FRIENDS`** entries are accessible only to the owner or a friend.
* **`DELETED`** entries are hidden.

### Story Behavior Notes

**US #40:**
If someone has a direct URL to a public or unlisted entry, they can access it through the single-entry endpoint.

**US #41:**
Friends-only entries are not available to strangers even if the stranger has the direct link.

**US #44:**
This endpoint is part of the “shareable link” behavior. A public or unlisted entry has a stable URL that can be sent to others through email, Discord, Slack, or similar tools.

**US #91:**
The owner can always access their own non-deleted entries directly, even when visibility is not public.

### Expected Status Codes

* **`200 OK`**: Successfully retrieved the entry.
* **`403 Forbidden`**: The requester is not allowed to view the entry.
* **`404 Not Found`**: The entry does not exist, or its visibility is set to `DELETED`.

---

### B. Create Entry (Auto-generated ID)

**URL:** `POST /api/authors/{AUTHOR_SERIAL}/entries/`
**Relevant User Stories:** #10, #14, #15, #16

* **When to use it:** When a local author is creating a brand new entry and wants the server to assign it a unique ID.
* **How to use it:** Send a POST request with the entry details in the body. Must be authenticated locally as the author.
* **Why to use it:** Standard way for the frontend to create entries without generating UUIDs client-side.

### Supported Content Types

Typical supported values include:

* `text/plain`
* `text/markdown`
* `image/png;base64`
* `image/jpeg;base64`

### Story Behavior Notes

**US #10:**
This is the main API for creating a new entry.

**US #14:**
If `contentType` is `text/plain`, the entry is treated as plain text content.

**US #15:**
If `contentType` is `text/markdown`, the entry is treated as CommonMark/Markdown content.

**US #16:**
If `contentType` is an image base64 type such as `image/png;base64` or `image/jpeg;base64`, the entry is treated as an image entry.

### Expected Status Codes

* **`201 Created`**: The entry was successfully generated and saved.
* **`400 Bad Request`**: Missing required fields in the JSON payload.
* **`403 Forbidden`**: The requester is not logged in or is not the target author.
* **`404 Not Found`**: The target author does not exist.

---

### C. Update / Create Entry (Specific ID)

**URL:** `PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`
**Relevant User Stories:** #12, #22

* **When to use it:** When a local author is editing an existing post, or when a remote node is pushing an entry to a local inbox.
* **How to use it:** Send a PUT request with the full entry object. Must be authenticated locally.
* **Why to use it:** It allows idempotent updating, and also supports create-with-specified-ID behavior.

### Story Behavior Notes

**US #12:**
This endpoint allows an author to edit their own entry content, description, title, and visibility.

**US #22:**
This endpoint is owner-protected. Another author cannot update someone else’s entry.

**US #13:** 
Successfully updating a local entry triggers an immediate re-push to all remote followers.

**US #45:** 
If the `contentType` is an image, the base64 payload is pushed to remote inboxes, allowing remote authors to view the image locally on their node.

### Expected Status Codes

* **`200 OK`**: The entry was successfully updated.
  **Note:** In the current implementation, this is also the response when a new entry is created through `PUT`.
* **`400 Bad Request`**: Invalid request body, such as unsupported visibility.
* **`403 Forbidden`**: The requester is not allowed to modify this entry.
* **`404 Not Found`**: The target author does not exist.

---

### D. Delete Entry

**URL:** `DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`
**Relevant User Stories:** #17, #22, #42, #78

* **When to use it:** When an author wants to remove their own entry.
* **How to use it:** Send a DELETE request. Must be authenticated locally.
* **Why to use it:** Performs a soft-delete by changing the visibility to `DELETED`, so it no longer appears in feeds or normal entry APIs.

### Story Behavior Notes

**US #17:**
Authors can delete their own entries.

**US #22:**
Authors cannot delete entries belonging to someone else.

**US #42:**
Once deleted, the entry is hidden from ordinary readers and normal entry APIs.

**US #78:**
Deletion is implemented as a **soft delete**, not a hard delete. The entry remains in the database, but it is removed from normal API/UI access.

**US #23:** Unlike a standard API, this triggers an outgoing `POST` to remote nodes. It uses the `EntryDelivery` model to ensure that *only* those who originally saw the post are notified of its deletion.

### Expected Status Codes

* **`204 No Content`**: The entry was successfully soft-deleted.
* **`403 Forbidden`**: The requester is attempting to delete an entry belonging to another author.
* **`404 Not Found`**: The entry does not exist.

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
## Browse Public Entries (US #46)

**URL:** `GET /api/entries/public/?page=<page>&size=<size>`  
**Relevant User Stories:** #46, #91

* **When to use it:**  
  To retrieve all public entries in the system, including local public entries and entries received in any inbox.  
  Useful for “explore” pages or feeds visible to all users, including unauthenticated ones.

* **How to use it:**  
  Send a GET request. Optional query parameters: `page` (default 1), `size` (default 5).  
  Example: `/api/entries/public/?page=2&size=5`

* **Why to use it:**  
  Provides a paginated list of public entries.  
  Enforces visibility rules (PUBLIC only).  
  Supports frontend feed rendering without needing per-author requests.

* **Why Not to use it:**  
  Returns only PUBLIC entries.  
  Remote/federated inbox entries will be merged after inbox implementation.  
  Do not use if you need entries visible only to friends or followers.
  Do not use this as a substitute for the 'Stream' or 'Inbox'. This endpoint is for discovery of global public content, not for viewing private interactions or friend updates
  Note: in the current implementation, this endpoint returns **local public entries only**. Public entries received from remote inboxes are not yet merged here.

### Story Behavior Notes

**US #46:**
This endpoint supports browsing the public posts of the local node beyond only authors the viewer follows. It is suitable for a public feed or explore page.

### Request Parameters

* `page`: integer, default 1 — Page number for pagination.  
* `size`: integer, default 5 — Number of entries per page.

### Expected Status Codes

* **`200 OK`**: Successfully retrieved the paginated list of public entries.

### Response Example

```json
{
  "page_number": 1,
  "size": 5,
  "count": 8,
  "src": [
    {
      "type": "entry",
      "title": "Public Entry 1",
      "id": "http://node/api/authors/1/entries/123",
      "description": "Description 1",
      "contentType": "text/plain",
      "content": "Content 1",
      "author": { "type": "author", "id": "http://node/api/authors/1" },
      "comments": { "type": "comments", "count": 0, "src": [] },
      "likes": { "type": "likes", "count": 0, "src": [] },
      "published": "2026-03-12T10:00:00+00:00",
      "visibility": "PUBLIC"
    }
  ]
}
```

---

## Image Proxy API

**URL 1:** `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image`
**URL 2:** `GET /api/entries/{ENTRY_FQID}/image`

**Relevant User Stories:** #16, #18, #41, #65

* **When to use it:** Use this to render an image entry directly inside an HTML `<img>` tag, or to embed images within a CommonMark entry.
* **How to use it:** Place this URL in the `src` attribute of an image tag. It decodes the base64 content on the fly.
* **Why to use it:** It returns raw binary data with the correct `Content-Type` header (for example, `image/png`). It automates base64 decoding so the frontend client does not need to parse JSON just to display a picture.

### Story Behavior Notes

**US #16:**
Image entries are stored as base64 content in an entry and exposed through this endpoint as real image bytes.

**US #18:**
Markdown entries can link to image-entry URLs or valid external image URLs, which allows images to appear inside CommonMark-rendered content.

**US #41:**
If the image belongs to a friends-only entry, the image endpoint applies the same visibility restrictions and prevents strangers from accessing it.

**US #65:**
This node can host images locally as image entries. Node admins can upload images through the web interface or create image entries through the API using base64 image content. 
1. **Author-hosted image entries** — authors can upload images as image entries (`image/png;base64` or `image/jpeg;base64`). These are served through the image API endpoint and can be reused in Markdown with stable local URLs.

2. **Admin-hosted images** — the node admin can also upload shared hosted images (`image/png;base64` or `image/jpeg;base64`). These are exposed in the entry authoring form as reusable local image URLs (`app/hosted-images/<int:image_id>/image/`), so authors can paste or insert them into CommonMark content.

This means users can embed both their own image-entry URLs and admin-provided hosted image URLs in Markdown while keeping the images hosted on the local node. 

### Expected Status Codes

* **`200 OK`**: Successfully returns the decoded binary image file.
* **`403 Forbidden`**: The image belongs to a `FRIENDS` entry and the requester is not allowed to view it.
* **`404 Not Found`**: The entry does not exist, is `DELETED`, or is not an image entry.
* **`500 Internal Server Error`**: The image content exists but could not be decoded.

### Example
**Direct Local Access:**
Use this when you know the local author and entry serial.
```
GET http://nodeaaaa/api/authors/111/entries/1145141919810/image
```
**FQID Proxy Access:**
Use this when you have the Fully Qualified ID of an entry from a remote node and want your local node to proxy the image for you.
```
GET http://nodebbbb/api/entries/http%3A%2F%2Fnodeaaaa%2Fapi%2Fauthors%2F111%2Fentries%2F1145141919810/image
```

## Markdown Support

**Relevant User Stories:** #15, #18, #21, #65

* **When to use it:** For entries whose `contentType` is `text/markdown`.
* **How it works in the web UI:** Markdown is rendered into safe HTML for browser display.
* **How it works in the API:** The API stores and returns markdown content as entry content. Clients can render it appropriately.
* **Why to use it:** Supports rich text authoring and image rendering while still allowing safe browser-based viewing.

### Story Behavior Notes

**US #15:**
Markdown entries are supported as a distinct content type from plain text entries. This allows authors to write formatted posts using CommonMark syntax.

**US #18:**
Markdown content can include image links, and those links can point to image-entry endpoints, preset node-admin hosted images, or valid external image URLs.

**US #21:**
In the web UI, markdown can be authored in the browser and rendered safely for display.

**US #65:**
Node-hosted images can be referenced from Markdown using the local image-entry endpoint, which lets users embed images stored on their own node.

### Example

```json
{
    "title": "Markdown Example",
    "description": "Testing markdown",
    "contentType": "text/markdown",
    "content": "# Hello\n\nThis is **bold** and this is ![an image](http://node/api/authors/123/entries/456/image)
    # Admin Hosted Image:
    ![](http://127.0.0.1:8000/app/hosted-images/6/image/)",
    "visibility": "PUBLIC"
}
```

This supports:

* CommonMark entries
* Image links inside markdown
* Browser authoring and viewing

---

## Shareable Link Behavior

**Relevant User Stories:** #40, #44

Entries support shareable URLs in both web-facing and API-facing forms.

### Web link

A reader can open a human-readable page such as:

```text
/app/entry/{ENTRY_ID}/
```

### API link

A reader or client can open the API form such as:

```text
/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}
```

or

```text
/api/entries/{ENTRY_FQID}/
```

### Story Behavior Notes

**US #40:**
Public and unlisted entries are accessible if someone has the direct link.

**US #44:**
These stable URLs can be shared externally in email, Discord, Slack, or similar tools.

**Restriction:**
Friends-only entries are not made public just because the link is shared. The server still checks visibility rules.

---

## Soft Delete Behavior

**Relevant User Stories:** #42, #78, #91

Deletion is implemented using a visibility change to `DELETED`.

### What that means

* The entry is **not removed from the database**.
* The entry disappears from author-entry lists.
* The entry disappears from public browse results.
* Single-entry reads treat the entry as unavailable.
* The owner no longer sees it through normal entry APIs after deletion.

### Story Behavior Notes

**US #42:**
Deleted entries are hidden from ordinary readers and APIs.

**US #78:**
Deleted entries remain stored in the database for administrative purposes.

**US #91:**
Entries remain visible to their owner until they are deleted. After deletion, they are no longer returned through normal entry APIs.

---
## Access Control Summary

| Visibility | Who can see it? | Relevant Story | API Behavior |
| --- | --- | --- | --- |
| **PUBLIC** | Everyone (even unauthenticated) | **#34** | Returned in all GET requests. |
| **FRIENDS** | Local Friends only | **#36, #41** | `403 Forbidden` if not a friend. |
| **UNLISTED** | Anyone with the link | **#35, #40** | Hidden from feeds, but `200 OK` via FQID. |
| **DELETED** | Node Admin only | **#42, #78** | `404 Not Found` for all users. |

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
| `is_remote` | `boolean` | `true` | Internal flag used by the stream to identify content pulled from other nodes. |
| `remote_web` | `string` | `"http://nodeb/..."` | The original browser-facing URL of a remote post. |


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

## Notes / Current Implementation Details
* `DELETED` entries remain in the database to support **US #78**, but they are hidden from normal UI and API reads.
* `UNLISTED` entries are visible through direct links, which is important for **US #35**, **US #40**, and **US #44**.
* `PUT` currently supports both updating an existing entry and creating a new one with a specific ID, but in the current implementation it returns `200 OK` for both cases.
* `GET /api/entries/public/` currently returns **local public entries only**.

## Entry Federation (The "Push" Logic)
### Automated Federation Logic
Whenever an entry is created, updated, or deleted via the API, the server automatically triggers federation to remote nodes.

* **Creation & Updates (US #11, #13, #45):** * The system identifies all remote followers and mutual friends.
    * The entry (including image data if applicable) is serialized into the standard JSON Entry Object.
    * The node performs a `POST` request to the remote author's `/inbox`.
* **Deletion (US #23):** * The system looks up the `EntryDelivery` table to find every remote recipient who previously received the entry.
    * It re-sends the entry with the `visibility` set to `DELETED` to ensure the remote node removes it from their UI/Cache.

### Expected Federation Behavior
| Action | Method | Destination | Content |
| :--- | :--- | :--- | :--- |
| **New Post** | `POST` | `/api/authors/{ID}/inbox/` | Full Entry Object |
| **Edit Post** | `POST` | `/api/authors/{ID}/inbox/` | Updated Entry Object |
| **Delete Post** | `POST` | `/api/authors/{ID}/inbox/` | Entry Object with `visibility: DELETED` |

---

## Remote Fetching (Incoming Node)
**Relevant User Story:** #46 (Remote aspect)

**Internal Function:** `fetch_remote_public_entries`

While the Inbox receives "pushed" content, this logic is used to actively "pull" content from other nodes for a user's stream.

* **How it works:** 
    1. The node iterates through all configured `IncomingNode` objects.
    2. It authenticates using stored credentials and fetches the author list from `{node}/api/authors/`.
    3. For each author, it fetches their public entries.
    4. **Advanced Visibility:** If the local user is a friend of the remote author, the node includes the `X-Requested-By` header (containing the local user's FQID). This tells the remote node it is safe to return `FRIENDS` visibility posts.

### Request Header for Friend Access
```http
GET /api/authors/{REMOTE_ID}/entries/ HTTP/1.1
Host: remote-node.com
Accept: application/json
X-Requested-By: https://your-node.com/api/authors/your-id
```

---

## Entry Federation (Outgoing Node)

### Purpose
To ensure that content created on a local node is automatically distributed to authorized remote followers and friends without them needing to pull the data manually.

### How it works
Whenever a local entry is **created, updated, or deleted**, the server triggers a background federation process:

1.  **Recipient Discovery:** The system identifies remote recipients based on the entry's `visibility`:
    * **PUBLIC / UNLISTED:** Sent to all remote followers and mutual friends.
    * **FRIENDS:** Sent only to remote mutual friends (local follows remote AND remote follows local).
    * **DELETED:** Sent to every remote author who previously received a version of this entry (tracked via `EntryDelivery` records).
2.  **Serialization:** The entry is converted to the standard JSON Entry Object.
3.  **Delivery:** The node performs a `POST` request to each recipient's **Inbox** (`/api/authors/{AUTHOR_FQID}/inbox/`).
4.  **Authentication:** Our node authenticates to the remote node using credentials stored in the `IncomingNode` table.


### Expected Federation Behavior
| Action | Triggering Endpoint | Federation Method | Payload `visibility` |
| :--- | :--- | :--- | :--- |
| **Create** | `POST /api/authors/.../entries/` | `POST` to Inbox | `PUBLIC`, `FRIENDS`, or `UNLISTED` |
| **Edit** | `PUT /api/authors/.../entries/{id}` | `POST` to Inbox | Updated visibility status |
| **Delete** | `DELETE /api/authors/.../entries/{id}` | `POST` to Inbox | `DELETED` |

---

## Inbox API

**URL:** `POST /api/authors/{AUTHOR_SERIAL}/inbox/`

* **When to use it:** When a remote node wants to send an entry, like, comment, or follow request to a local author.
* **Behavior for Entries:** Currently, the inbox receives the object and returns a `202 Accepted` status.
* **Note:** Per current implementation, `_inbox_handle_entry` logs the receipt but does not yet persist the remote entry into the local database.

### Expected Status Codes
* **`202 Accepted`**: The object was received and routed to the correct handler.
* **`401 Unauthorized`**: The remote node failed to provide valid `Basic Auth` credentials matching an `IncomingNode` entry.
* **`404 Not Found`**: The target local author does not exist.

---