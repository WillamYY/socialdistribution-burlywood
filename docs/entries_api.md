# Entries and Image API Documentation

This document covers the API implementation and expected behavior for **Entries, Markdown, and Image** user stories, referencing GitHub issues.

### User Stories Covered
* **#10**: As an author, I want to make entries.
* **#12**: As an author, I want to edit my entries locally.
* **#14**: As an author, entries I make can be in simple plain text.
* **#15**: As an author, entries I make can be in CommonMark.
* **#16**: As an author, entries I create can be images.
* **#17**: As an author, I want to delete my own entries locally.
* **#18**: As an author, CommonMark entries can link to images.
* **#21**: As an author, I want to be able to use my web-browser to manage/author my entries.
* **#22**: As an author, other authors cannot modify my entries.

---

## Web Interface for Authors (US #21)

### Purpose
To provide a user-friendly, browser-based management system for authors to create, edit, and delete their entries without using technical API tools or interfaces like Swagger.

### Implemented Routes
* **Creation**: `/app/create-entry/` - A dedicated form for authoring new posts.
* **Management**: `/app/my-entries/` - A personal dashboard where authors can view, edit, or delete their existing content.
* **Viewing**: `/app/stream/` - A human-readable feed of posts from the author and their friends.

### How it works
* **Session-Based**: The web interface relies on `request.session['author_id']` to manage state and permissions.
* **Rendering**: The interface uses Django Templates to render database content into sanitized HTML, automatically handling Markdown conversion for the user.

---

## Get Author Entries (Paginated)
**URL:** `GET /api/authors/{AUTHOR_ID}/entries/`

### When to use it
* Use this to retrieve a list of all public entries belonging to a specific author.

### How to use it
* Supports optional query parameters `page` and `size`. 
* Default: `page=1`, `size=5`.

### Why/Why Not to use it
* **Why**: It strictly follows the project's pagination requirements for author-specific content.
* **Why Not**: This endpoint only returns `PUBLIC` entries. To see a combined feed including friends-only posts, use the `Stream` API instead.

### Response JSON Fields
| Field | Type | Example | Purpose |
| :--- | :--- | :--- | :--- |
| `type` | `string` | `"entries"` | Identifies the object type. |
| `page_number` | `integer` | `1` | The current page index. |
| `size` | `integer` | `5` | Number of items in the current response. |
| `count` | `integer` | `24` | Total number of public entries available for this author. |
| `src` | `array` | `[...]` | A list of Entry objects. |

---

## Get Single Entry
**URL:** `GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/`

### When to use it
* Use this to get the full details, including comments and likes, for a specific post.

### Why/Why Not to use it
* **Why Not**: If the entry's `visibility` is `DELETED`, this endpoint will return a `404 Not Found`.

### Response JSON Fields (Entry Object)
| Field | Type | Example | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | `string` | `"http://.../entries/uuid"` | The Fully Qualified ID (URL) of the entry. |
| `contentType` | `string` | `"text/markdown"` | Specifies if content is `text/plain`, `text/markdown`, or an image type. |
| `content` | `string` | `"<h2>Hello</h2>"` | The raw text or rendered HTML (for Markdown). |
| `visibility` | `string` | `"PUBLIC"` | Access level: `PUBLIC`, `FRIENDS`, `DELETED`, etc. |

---

## Image Proxy (US #16, #18)
**URL:** `GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/image`
**Secondary URL:** `GET /api/entries/{ENTRY_ID}/image`
**Any valid external image URL*s*

### When to use it
* Use this to render an image entry directly in an HTML `<img>` tag.
* Necessary for CommonMark entries that want to embed images stored on the node.

### How to use it
* This endpoint does **not** return JSON. It returns raw binary data with the appropriate `Content-Type` header (e.g., `image/png`).

### Why/Why Not to use it
* **Why**: It automates the decoding of Base64 data so the client doesn't have to.
* **Why Not**: Will return `404` if the entry requested is a text-based post.

---

## Create/Update/Delete Entry (Security US #22)
**URL:** `PUT /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/` (Create/Update)
**URL:** `DELETE /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/` (Delete)

### Behavior
* **PUT**: Updates existing entries or creates a new entry with the specified `ENTRY_ID`.
* **DELETE**: Performs a **Soft Delete** by setting `visibility` to `DELETED`. The record remains in the database but is hidden from all API and Web views.

### Security Isolation
To satisfy **US #22**, the `session['author_id']` must match the `{AUTHOR_ID}` in the URL. Any attempt by an author to modify or delete another author's entry will result in a **403 Forbidden** response.

---

## Content Rendering (US #14, #15)

### Markdown vs. Plain Text
* **text/markdown**: Content is rendered into sanitized HTML using the CommonMark standard.
* **text/plain**: Content is treated as raw text with no formatting applied.

### JSON Fields (Request/PUT)
| Field | Type | Example | Purpose |
| :--- | :--- | :--- | :--- |
| `title` | `string` | `"My Post"` | The title shown to users. |
| `content` | `string` | `"**Hello**"` | The raw content (Markdown, Plain Text, or Base64). |
| `contentType` | `string` | `"text/markdown"` | The MIME type of the content. |
| `visibility` | `string` | `"PUBLIC"` | Who can see the post. |