# Node Connection Authentication API Documentation

This document covers the authentication between two nodes and expected behavior for **Node management** user stories, referencing GitHub issues.

Node management (#68, #72, #73, #74)
Node management (#68, #72, #73, #74, #80)

* **#68** As a node admin, I want to be able to connect to remote nodes by entering only the URL of the remote node, a username, and a password, so that I don't have to edit code.
* **#72** As a node admin, I can prevent nodes from connecting to my node if they don't have a valid username and password.
* **#73** As a node admin, node to node connections can be authenticated with HTTP Basic Auth, so that I don't have to deal with tokens.
* **#74** As a node admin, I can disable the node to node interfaces for connections that I no longer want, in case another node goes bad.
* **#80** As a node admin, I want the API objects (authors, entries, etc.) to be [identified by their full URL](https://uofa-cmput404.github.io/general/project.html#ids), to prevent collisions with other node's numbering schemes.

node Management
Click a value to filter the view


## Overview

Suppose node A wants to share with node B, and node B agrees to receive information from node A. Then the node admin of node A and node B must create a one way connection from node A to node B. When a user accesses node B, they will obtain the information that was shared from node A on top of the information in node B. In order for this to happen, node B must request the information from node A's database. However, when node A receives the request from node B, node A must make sure the request is actually sent by node B by checking the Basic auth username and password in the request (**US #68, #73**). If the credentials in the request are invalid, then node A should not share its information in the response (**US #72**). At the same time, if node A does not wish to share its information with node B, node A could close its own end of the connection; if node B does not wish to receive information from node A, node B could its own end of the connection (**US #74**).
Additionally, to support distributed systems: All shared API objects must be identified using full URLs instead of local IDs (**US #80**).
## How to use

### 1. Communication between node admins

For a one way connection between node A and node B (suppose node A is sending information to node B), both admins of node A and node B need to first communicate. The admins must "agree" on a single set containing the username and the password to be used; the username and password will be used to authenticate node B when the request reaches node A. The admins must also be aware of each other's base URLs (**US #68**).

### 2. Configuration on the sharing node

Knowing that node B wants to receive information from node A, it must create an entry in the **Incoming nodes** table. An **Incoming nodes** entry contains the following fields:
- **Url**
    - The Url field must follow the form `http[s]://service/`
        - `http[s]` indicates that is both `http` and `https` are supported (in case node A does not support https)
        - The `service` indicates the domain name mapping to the IP address of node A. It could also just be the IP address of node A.
- **Username**
    - The username that will be used to authenticate node B. This will be sent in the request to node A.
- **Password**
    - The password that will be used to authenticate node B. This will be sent in the request to node A.

### 3. Configuration on the sharing node

Knowing that node A wants to share information with node B, it must create an entry in the **Outgoing nodes** table. An **Outgoing nodes** entry contains the following fields:
- **Url**
    - The Url field must follow the form `http[s]://service/`
        - `http[s]` indicates that is both `http` and `https` are supported (in case node B does not support https)
        - The `service` indicates the domain name mapping to the IP address of node B. It could also just be the IP address of node B.
- **Username**
    - The username that will be used to authenticate node B. Upon receiving the request from node B, node A will check whether the provided username matches this username.
- **Password**
    - The password that will be used to authenticate node B. Upon receiving the request from node B, node A will check 

### 4. Usage

Once the configurations have been completed, any user that visits node B will be able to see the information that is shared from node A on top of all the information that is already on node B.

### 5. Disabling the connection on the receiver side

Suppose node B no longer wants to receive information shared by node A. This can be done by unchecking the `IS ACTIVE` field for the **Incoming node** entry corresponding to node A in node B's admin panel.

**NOTE:** By changing either the username, the password, the url, or by deleting the **Incoming nodes** entry corresponding to node A in node B's admin panel, this will also cause node B to stop receiving information from node A. However, this is not the proper way to prevent the connection.

### 6. Disabling the connection on the sender side

Suppose node A no longer wants to share information to node B. This can be done by unchecking the `IS ACTIVE` field for the **Outgoing node** entry corresponding to node B in node A's admin panel.

**NOTE:** By changing either the username, the password, the url, or by deleting the **Outgoing nodes** entry corresonding to node B in node A's admin panel, this will also cause node B to stop receiving information from node A. However, this is not the proper way to prevent the connection.

## Headers

The following headers are to be used when the receiving node sends a request to the sender node:
- `Authorization` → a **Basic** authorization header

## Status codes
- `200 OK` → Authentication was successful, and the resource requested was successfully processed
- `403 Forbidden` → This occurs when:
    - No authorization header was provided in the HTTP request
    - The type of authorization was not Basic
    - There was an error decoding the credentials
    - The credentials supplied were invalid
    - The sending node interface has been disabled

## Implementation

The implementation relies on the Django REST Framework authentication which authenticates the endpoint proceses the request. In this case, it will only allow API requests with the correct Basic auth to be processed. The structure of our node connections is as follows:

- Each node has 2 databases
    - **Incoming nodes** (to receive information from other nodes)
    - **Outgoing nodes** (to send information to other nodes)

### IncomingNodeAuthentication

This is the Authentication class that is used to setup Basic Auth within. The implementation is as follows:

- After populating the entries as instructing in the [How to use](#how-to-use) section, the following steps will be performed
    - The receiving node will check its **Incoming nodes** table to determine the nodes from which it should get information
    - For each entry, the receiving node will send a request to get information from the sending node, supplying the appropriate credentials (username and password) to each node as well as its own URL
    - The sending node will then validate the request by checking doing the following authentication checks:
        - The request must have an authorization header
        - The authentication type must be basic
        - No errors caused when decoding the credentials
        - The credentials entered are valid (the sending node found the **Outgoing nodes** entry containing the appropriate username and password)
        - The node must also have that database entry be active
    - If any of the checks do not pass, the sender will return a status code of `403`
    - If all of the checks do pass, the sender will return the appropriate data that was requested

# API Object Identification (US #80)
## Overview

In a distributed system with multiple nodes, different nodes may generate objects using their own local identifiers. This can lead to collisions when integrating data across nodes.

To prevent this, all API objects must be identified using full URLs instead of local IDs.
---

## ID Format

All API object IDs must follow the format:

http[s]://service/resource-path/id
---
## Examples
### Author
http://nodeaaaa/api/authors/111
### Entry (Post)
http://nodebbbb/api/authors/222/entries/249
### Comment
http://nodeaaaa/api/authors/111/commented/130

---

## Requirements

- All API objects must use full URLs as their id  
- Local IDs must not be used alone in API responses  
- IDs must remain consistent across all responses  
- IDs must not be modified when shared between nodes  

---

## Cross-node Behavior

When a node receives objects from another node:

- The full URL IDs must be preserved  
- IDs must not be replaced with local database IDs  
- IDs must be used as the unique identifier for the object  

---

## Benefits

- Prevents ID collisions across nodes  
- Ensures global uniqueness  
- Supports reliable data sharing between nodes  

---

## API Usage Examples

### Fetch Authors

#### Request
```http
GET /api/authors/ HTTP/1.1
Host: nodeA.com
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```
#### Response
```json
{
  "type": "authors",
  "items": [
    {
      "type": "author",
      "id": "http://nodeaaaa/api/authors/111",
      "host": "http://nodeaaaa/api/",
      "displayName": "Greg Johnson",
      "github": "http://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg"
    }
  ]
}
```
### Fetch Entries
#### Request
```http
GET /api/authors/111/entries/ HTTP/1.1
Host: nodeA.com
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```
#### Response
```json
{
  "type": "entries",
  "items": [
    {
      "type": "entry",
      "id": "http://nodebbbb/api/authors/222/entries/249",
      "author": {
        "id": "http://nodeaaaa/api/authors/111"
      },
      "content": "Hello world"
    }
  ]
}
```
## Fetch Comments
#### Request
```http
GET /api/authors/111/entries/249/comments/ HTTP/1.1
Host: nodeA.com
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```
#### Response

```json
{
  "type": "comments",
  "items": [
    {
      "type": "comment",
      "id": "http://nodeaaaa/api/authors/111/commented/130",
      "author": {
        "type": "author",
        "id": "http://nodeaaaa/api/authors/111",
        "host": "http://nodeaaaa/api/",
        "displayName": "Greg Johnson"
      },
      "comment": "Sick Olde English",
      "contentType": "text/markdown",
      "published": "2015-03-09T13:07:04+00:00",
      "entry": "http://nodebbbb/api/authors/222/entries/249"
    }
  ]
}
Error Example (Invalid Credentials)
{
  "detail": "Invalid authentication credentials."
}
```
