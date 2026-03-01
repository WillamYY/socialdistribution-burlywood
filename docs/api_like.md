# Views API Documentation

This document covers the API implementation and expected behavior for **Liking Entries** user stories, referencing GitHub issues.

## API User Stories
* **#58** Liking entries as an author
* **#60** Seeing the likes of a public entry

## Object Schemas
**Note:** \* Denotes a required field for POST body
### Like Object
* `type` → type of object
* `author`\* → author object defined by the following:
    * `type` → type of object
    * `id`\* → FQID of the person who liked the entry
    * `host` → host node of author
    * `displayName` → the displayed name of the author
    * `github` → the link to the author's github
    * `profileImage` → link to the author's profile picture
    * `web` → URL to webpage of author's profile
* `published` → date the entry was liked
* `id` → id of the like object
* `object`\* → object that was liked

### Likes Object
* `type` → type of object
* `web` → URL to webpage of entry
* `id` → endpoint used to query this object
* `page number` → current page number of likes 
* `size` → size of each page
* `count` → total number of likes on this query
* `src` → list of Like objects, [Like\[\]](#like-Object)

## Likes APIs

### Sending a like

**URL:** `POST /api/authors/{AUTHOR_ID}/inbox`\
**Description:** Sends a like to a remote author's entry

**POST Example:**

```
POST /api/authors/2/inbox
```

```json
{
    "type":"",
    "author":{
        "type":"",
        "id":"http://127.0.0.1:8000/api/authors/1",
        "displayName":"",
        "github": "",
        "profileImage": ""
    },
    "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
}
```

**POST Response:**

```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/1",
        "host": "http://127.0.0.1:8000/api/",
        "displayName": "displayName",
        "github": "github",
        "profileImage": null,
        "web": "http://127.0.0.1:8000/api/"
    },
    "published": "2026-03-01T12:30:07.085666-07:00",
    "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
    "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
}
```

### Status codes
* `201` → Like object successfully created
* `404` → Author or object not found
* `405` → Method not allowed on endpoint

### Listing an Entry's likes

**URL:** `GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/likes`\
**Description:** Getting all the likes for a given public or unlisted entry with a given author

**GET Response:**
```json
{
    "type": "likes",
    "web": "http://127.0.0.1:8000/app/author/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e",
    "id": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e/likes",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "displayName",
                "github": "github",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "published": "2026-03-01T12:30:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
        }
    ]
}
```

### Status codes
* `200` → Successfully returned query
* `404` → Author or object not found
* `405` → Method not allowed on endpoint

### Listing an Entry's likes (LOCAL)

**URL:** `GET /api/entries/{ENTRY_FQID}/likes`\
**Description:** Getting all the likes from local authors for a given public or unlisted entry

**GET Response:**
```json
{
    "type": "likes",
    "web": "http://127.0.0.1:8000/app/entries/http://127.0.0.1:8000/app/author/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e",
    "id": "http://127.0.0.1:8000/api/entries/http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e/likes",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "nevin",
                "github": "",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "published": "2026-03-01T12:30:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
        }
    ]
}
```

### Status codes
* `200` → Successfully returned query
* `404` → Entry FQID not found
* `405` → Method not allowed on endpoint

## Liked APIs

### Listing an author's likes

**URL:** `GET /api/authors/{AUTHOR_ID}/liked`\
**Description:** Getting all the public or unlisted entries liked by an author

**GET Response:**
```json
{
    "type": "likes",
    "web": "http://127.0.0.1:8000/app/author/1",
    "id": "http://127.0.0.1:8000/api/authors/1/liked",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "nevin",
                "github": "",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "published": "2026-03-01T12:30:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
        }
    ]
}
```

### Status codes
* `200` → Successfully returned query
* `404` → Author not found
* `405` → Method not allowed on endpoint

### Getting a single like object

**URL:** `GET /api/authors/{AUTHOR_ID}/liked/{LIKE_ID}`
**Description:** Gets a single like object created by an author

**GET Response:**

```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/1",
        "host": "http://127.0.0.1:8000/api/",
        "displayName": "displayName",
        "github": "github",
        "profileImage": null,
        "web": "http://127.0.0.1:8000/api/"
    },
    "published": "2026-03-01T12:30:07.085666-07:00",
    "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
    "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
}
```

### Status codes
* `200` → Successfully returned like object
* `404` → Author not found or like does not exist
* `405` → Method not allowed on endpoint

### Listing an author's likes (LOCAL)

**URL:** `GET /api/authors/{AUTHOR_FQID}/liked`\
**Description:** Getting all the public or unlisted entries liked by a local author

```json
{
    "type": "likes",
    "web": "http://127.0.0.1:8000/app/author/http://127.0.0.1:8000/app/author/1",
    "id": "http://127.0.0.1:8000/api/authors/http://127.0.0.1:8000/api/authors/1/liked",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://127.0.0.1:8000/api/authors/1",
                "host": "http://127.0.0.1:8000/api/",
                "displayName": "displayName",
                "github": "github",
                "profileImage": null,
                "web": "http://127.0.0.1:8000/api/"
            },
            "published": "2026-03-01T12:30:07.085666-07:00",
            "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
            "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
        }
    ]
}
```

### Status codes
* `200` → Successfully returned query
* `404` → Author not found
* `405` → Method not allowed on endpoint

### Getting a single like object (LOCAL)

**URL:** `GET /api/liked/{LIKE_FQID}`\
**Description:** Gets a single like object created by a local author

**GET Example:**

```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/1",
        "host": "http://127.0.0.1:8000/api/",
        "displayName": "displayName",
        "github": "github",
        "profileImage": null,
        "web": "http://127.0.0.1:8000/api/"
    },
    "published": "2026-03-01T12:30:07.085666-07:00",
    "id": "http://127.0.0.1:8000/api/authors/1/liked/51",
    "object": "http://127.0.0.1:8000/api/authors/2/entries/20de2d32-9dd0-421f-a7f7-2b5ef4670e9e"
}
```

### Status codes
* `200` → Successfully returned like
* `404` → Like not found
* `405` → Method not allowed on endpoint