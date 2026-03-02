# Views API Documentation

This document covers the API implementation and expected behavior for the **Author** user stories, referencing GitHub issues.

## API User Stories
* **#2** Consistent ID for author
* **#3** Multiple authors on a node
* **#4** Public page of author

## Object Schemas
### Author Object
* `type` → type of object
* `id` → API URL of the author
* `host` → URL to the host hosting the author
* `displayName` → the name the author will display on the website
* `github` → URL to the github of the author
* `profileImage` → URL to the authors profile picture
* `web` → URL to the authors webpage on the base website

### Authors Object
* `type` → type of object
* `authors` → list of Author objects

## Single Author and Authors APIs

### Getting A User

**URL:** `GET api/authors/{AUTHOR_SERIAL}/`\
**Description:** Gets the author associated with the author serial ID

**GET Example:**

```
GET /api/authors/1/
```

**GET Response:**

```json

{
    "type": "author",
    "id": "http://localhost:8000/admin/api/authors/1",
    "host": "http://localhost:8000/admin/api/",
    "displayName": "John Doe",
    "github": "https://github.com/dwlow",
    "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
    "web": "http://localhost:8000/app/authors/1"
}
```

### Status codes
* `200` → If the author is found
* `404` → If author does not exist

### Adding an author

**URL:** `PUT api/authors/{AUTHOR_SERIAL}/`\
**Description:** Adds the author information to the

**Example PUT:**

```
PUT /api/authors/2/
```

```json
{
    "type": "author",
    "id": "http://localhost:8000/admin/api/authors/2",
    "host": "http://localhost:8000/admin/api/",
    "displayName": "Jane Doe",
    "github": "https://github.com/jane",
    "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
    "web": "http://localhost:8000/app/authors/2"
}
```

**PUT Response:**
```json

{
    "type": "author",
    "id": "http://localhost:8000/admin/api/authors/2",
    "host": "http://localhost:8000/admin/api/",
    "displayName": "Jane Doe",
    "github": "https://github.com/jane",
    "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
    "web": "http://localhost:8000/app/authors/2"
}
```

### Status codes
* `200` → Successfully updated author info or created author request
* `400` → If request parameters is invalid
* `405` → Method not allowed on endpoint

### Displaying list of authors

**URL:** `GET api/authors/`
**Description:** Gets authors in the database

**GET Response:**
```json
{
    "type": "authors",
    "authors": [
        {
            "type": "author",
            "id": "http://localhost:8000/admin/api/authors/1",
            "host": "http://localhost:8000/admin/api/",
            "displayName": "John Doe",
            "github": "https://github.com/dwlow",
            "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
            "web": "http://localhost:8000/app/authors/1"
        },
        {
            "type": "author",
            "id": "http://localhost:8000/admin/api/authors/2",
            "host": "http://localhost:8000/admin/api/",
            "displayName": "Jane Doe",
            "github": "https://github.com/jane",
            "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
            "web": "http://localhost:8000/app/authors/2"
        }
    ]
}
```

### Status codes
* `200` → Successfully returned query
* `405` → Method not allowed on endpoint