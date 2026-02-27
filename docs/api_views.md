# Views API Documentation

This document covers the API implementation and expected behavior for **Identity and Following/Friends** user stories, referencing GitHub issues.

Identity (#7, #8)

* **#7** Edit profile: name, description, picture, GitHub
* **#8** Manage profile in web browser

Following/Friends (#48, #50, #51, #52, #53, #54)

* **#48** Follow local authors to see their entries
* **#50** Approve/deny other authors following me
* **#51** See pending follow requests
* **#52** Unfollow authors I am following
* **#53** Mutual following makes us friends
* **#54** Unfriend authors by unfollowing

# Common Notes

* All endpoints under `http://127.0.0.1:8000/api/`
* Local endpoints require `auth_id` query parameter to match the author ID
* All endpoints return JSON
* Status codes:

  * `200 OK` → successful GET/PUT/POST
  * `201 Created` → successful POST
  * `204 No Content` → successful DELETE
  * `403 Forbidden` → authentication failure
  * `404 Not Found` → resource not found
  * `409 Conflict` → request conflicts with existing state

# Identity APIs

### Edit Profile

**URL:** `PUT /api/authors/{AUTHOR_ID}/profile/`
**Description:** Retrieve or update profile of the logged-in author

**Authentication:** `auth_id` must match `{AUTHOR_ID}`

**GET Example:**

```
GET /api/authors/1/profile/?auth_id=1
```

```json
{
  "username": "Alex",
  "name": "Alex Johnson",
  "description": "Hello, I am Alex!",
  "github": "https://github.com/alexjohnson",
  "picture": "http://127.0.0.1:8000/media/profile_pics/alex.png"
}
```

**PUT Example:**

```
PUT /api/authors/1/profile/?auth_id=1
```

```json
{
  "name": "Alex Johnson",
  "description": "Hello, I am Alex!",
  "github": "https://github.com/alexjohnson",
  "picture": "<file upload>"
}
```

**PUT Response:**

```json
{
  "detail": "Profile updated successfully"
}
```

**Notes:** Only `name`, `description`, `github`, and `picture` can be updated

# Following/Friends APIs

### List Following Authors

**URL:** `GET /api/authors/{AUTHOR_ID}/following/`
**Authentication:** `auth_id` must match `{AUTHOR_ID}`

**Response Example:**

```json
{
  "following": [
    {
      "type": "author",
      "id": "http://127.0.0.1:8000/api/authors/2",
      "host": "http://127.0.0.1:8000/api/",
      "displayName": "Sandra Smith",
      "github": "https://github.com/sandrasmith",
      "profileImage": "http://127.0.0.1:8000/media/profile_pics/sandra.png",
      "web": "http://127.0.0.1:8000/user/2/"
    }
  ]
}
```

### Follow an Author

**URL:** `POST /api/authors/{AUTHOR_ID}/follow/`
**Authentication:** `auth_id` must match `{AUTHOR_ID}`

**Responses:**

* `201 Created` → Follow request sent
* `409 Conflict` → Already following or request already sent
* `403 Forbidden` → Cannot follow yourself

### List Follow Requests

**URL:** `GET /api/authors/{AUTHOR_ID}/follow-requests/`
**Authentication:** `auth_id` must match `{AUTHOR_ID}`

**Response Example:**

```json
{
  "follow_requests": [
    {
      "id": 1,
      "requester_id": 3,
      "requester_username": "charlie"
    }
  ]
}
```

### Approve a Follow Request

**URL:** `POST /api/follow-requests/approve/{REQUEST_ID}/`
**Response Example:**

```json
{
  "detail": "Follow request approved"
}
```

### Deny a Follow Request

**URL:** `POST /api/follow-requests/deny/{REQUEST_ID}/`
**Response Example:**

```json
{
  "detail": "Follow request denied"
}
```

### Unfollow an Author

**URL:** `DELETE /api/authors/{AUTHOR_ID}/following/{FOREIGN_AUTHOR_ID}/`
**Response:** `204 No Content` → success

### List Friends

**URL:** `GET /api/authors/{AUTHOR_ID}/friends/`
**Authentication:** `auth_id` must match `{AUTHOR_ID}`

**Response Example:**

```json
{
  "friends": [
    {
      "id": 2,
      "username": "sandra"
    }
  ]
}
```
# Example Objects

**Author Object:**

```json
{
  "type": "author",
  "id": "http://127.0.0.1:8000/api/authors/1",
  "host": "http://127.0.0.1:8000/api/",
  "displayName": "Alex Johnson",
  "github": "https://github.com/alexjohnson",
  "profileImage": "http://127.0.0.1:8000/media/profile_pics/alex.png",
  "web": "http://127.0.0.1:8000/user/1/"
}
```

**Follow Object:**

```json
{
  "type": "follow",
  "summary": "Alex wants to follow Sandra",
  "actor": {
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/1",
    "displayName": "Alex Johnson",
    "github": "https://github.com/alexjohnson",
    "profileImage": "http://127.0.0.1:8000/media/profile_pics/alex.png",
    "web": "http://127.0.0.1:8000/user/1/"
  },
  "object": {
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/2",
    "displayName": "Sandra Smith",
    "github": "https://github.com/sandrasmith",
    "profileImage": "http://127.0.0.1:8000/media/profile_pics/sandra.png",
    "web": "http://127.0.0.1:8000/user/2/"
  }
}
```
