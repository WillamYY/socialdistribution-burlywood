# Comments API Documentation

This document covers the API implementation and expected behavior for **Commenting on Entries** user stories, referencing GitHub issues.

## API User Stories
* **#62** Comment visibility on friends-only entries
* **#59** Commenting on entries as an author

## Object Schemas
**Note:** \* Denotes a required field for POST body

### Comment Object
* `type` → type of object
* `author`\* → author object defined by the following:
    * `type` → type of object
    * `id`\* → FQID of the author of the comment
    * `host` → host node of author
    * `displayName` → displayed name of the author
    * `github` → link to author's github
    * `profileImage` → link to profile picture
    * `web` → URL to author profile page
* `comment`\* → text content of the comment
* `contentType` → format of comment (e.g. `text/plain`, `text/markdown`)
* `published` → date the comment was created
* `id` → id of the comment object
* `object`\* → FQID of the entry being commented on

### Comments Object
* `type` → type of object
* `id` → endpoint used to query this object
* `page_number` → current page number
* `size` → size of each page
* `count` → total number of comments
* `src` → list of Comment objects, [Comment[]](#comment-object)

---

## Comments APIs

### Creating a comment

**URL:** `POST /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments`  
**Description:** Creates a comment on a local entry

**POST Example:**
POST /api/authors/2/entries/20de2d32/comments
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
Status codes

201 → Comment successfully created

401 → Login required to comment

403 → Author cannot access this entry

404 → Author or entry not found

405 → Method not allowed on endpoint


URL: GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments
Description: Returns all comments visible to the requesting user
{
    "type": "comments",
    "id": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32/comments",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "displayName",
                "github": "",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "comment": "Nice post!",
            "contentType": "text/plain",
            "published": "2026-03-01T13:10:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/commented/99",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32"
        }
    ]
}
Status codes

200 → Successfully returned comments

403 → Entry not visible to requester

404 → Author or entry not found

405 → Method not allowed on endpoint


URL: GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments
Description: Returns all comments visible to the requesting user
{
    "type": "comments",
    "id": "http://127.0.0.1:8000/api/entries/http://127.0.0.1:8000/api/authors/2/entries/20de2d32/comments",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "displayName",
                "github": "",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "comment": "Nice post!",
            "contentType": "text/plain",
            "published": "2026-03-01T13:10:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/commented/99",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32"
        }
    ]
}
Status codes

200 → Successfully returned comments

404 → Entry FQID not found

405 → Method not allowed on endpoint


Some documentation text was generated with the assistance of ChatGPT (OpenAI, https://chatgpt.com) on March 1, 2026. The prompt is: Check my current comment api doc and add parts with similar structure to api_like.md.