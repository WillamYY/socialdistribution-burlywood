# Stream API Documentation

This document covers the API implementation and expected behavior for the **Stream** user stories:

- **#25** Stream shows all entries the author should know about
- **#26** Stream includes all public entries on the node
- **#27** Stream includes unlisted + friends-only entries from followed authors
- **#28** Stream shows the latest version of edited entries
- **#29** Stream excludes deleted entries
- **#31** Stream sorted with most recent entries first

Note: This API and documentation were added specifically for the Stream user stories block.

## Endpoint

`GET /api/authors/{AUTHOR_ID}/stream/`

### Authentication

Local API only. Requires a logged-in session for the author:

- `session.author_id` must exist
- `session.author_id` must match `{AUTHOR_ID}`

### Behavior

The stream returns:

- **All PUBLIC entries** from any author on this node
- **UNLISTED entries** from authors the viewer follows
- **FRIENDS entries** only from mutual followers (friends)
- **Deleted entries** are excluded (they are hard-deleted from the DB)
- Entries are **sorted by `published` in descending order**
- Edited entries always show the **latest content** stored in the DB

### Response Format

```json
{
  "type": "entries",
  "page_number": 1,
  "size": 2,
  "count": 2,
  "src": [
    {
      "type": "entry",
      "id": "5b6d0c53-6c64-4b78-9e8d-8c6b413c7e7a",
      "title": "My Public Post",
      "description": "Short description",
      "contentType": "text/plain",
      "content": "Hello world",
      "author": {
        "type": "author",
        "id": 1,
        "displayName": "Alice",
        "username": "alice"
      },
      "published": "2026-02-25T23:55:21.123456-07:00",
      "visibility": "PUBLIC",
      "likeCount": 3
    }
  ]
}
```

### Fields

- `type` (string): Always `"entries"`
- `page_number` (int): Always `1` (pagination not implemented yet)
- `size` (int): Number of entries returned
- `count` (int): Same as `size` (total entries in the response)
- `src` (array): Array of entry objects

Entry object fields:

- `type` (string): Always `"entry"`
- `id` (string): UUID of the entry
- `title` (string): Title of the entry
- `description` (string): Short description
- `contentType` (string): Content type (e.g. `text/plain`, `text/markdown`, `image/png;base64`)
- `content` (string): Rendered content (HTML for markdown, base64 for images)
- `author` (object): Author info (id, display name, username)
- `published` (string): ISO 8601 timestamp
- `visibility` (string): `PUBLIC`, `UNLISTED`, or `FRIENDS`
- `likeCount` (int): Number of likes on the entry

### Error Responses

```json
{ "detail": "Authentication required." }
```
Status: `401`

```json
{ "detail": "Forbidden." }
```
Status: `403`

```json
{ "detail": "Method not allowed." }
```
Status: `405`

### Citations
- Use of Cursor and Chatgpt (Gen AI tools) for debugging help during issues and for test cases.
