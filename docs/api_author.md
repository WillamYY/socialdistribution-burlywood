# Views API Documentation

This document covers the API implementation and expected behavior for the **Author** user stories, referencing GitHub issues.

## API User Stories
* **#2** Consistent ID for author
* **#3** Multiple authors on a node
* **#4** Public page of author
* **#77** No seperate database for front and backend

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

## Getting A Single User

**URL:** `GET api/authors/{AUTHOR_SERIAL}/`
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

## Adding an author

**URL:** `PUT api/authors/{AUTHOR_SERIAL}/`\
**Description:** Adds the author information to the

**Example PUT:**

```
PUT /api/authors/2/
```

```json
{
    "type": "author",
    "id": "http://localhost:8000/api/authors/2",
    "host": "http://localhost:8000/api/",
    "displayName": "Jane Doe",
    "github": "https://github.com/jane",
    "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
    "web": "http://localhost:8000/app/user/2"
}
```

**PUT Response:**
```json

{
    "type": "author",
    "id": "http://localhost:8000/api/authors/2",
    "host": "http://localhost:8000/api/",
    "displayName": "Jane Doe",
    "github": "https://github.com/jane",
    "profileImage": "https://miro.medium.com/v2/resize:fit:1400/1*uNCVd_VqFOcdxhsL71cT5Q.jpeg",
    "web": "http://localhost:8000/app/user/2"
}
```

### Status codes
* `200` → Successfully updated author info
* `201` → Successfully created a user request and sent it to the admin
* `400` → If the id of the user does not match the location it is being placed (eg. trying to place http://localhost:8000/api/authors/2 at the location of http://localhost:8000/api/authors/1)
* `400` → If the displayName of the user is already taken (eg. Adding a user with display name Jonathan1 when one already exists)
* `405` → Method not allowed on endpoint

## Displaying list of authors

**URL:** `GET api/authors/?page={page number}&size={size of each page}`
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

### Notes
* If the size is not present it will return every author on the node regardless of page number
* If the page number is not present it defaults to the first page
* If the page number is out of range an empty list of authors will be returned
* If there are not enough authors to satisfy the size of the page it will return only the number of authors it has for that page (If the page size is 5 but a page only has 3 it will only return 3)