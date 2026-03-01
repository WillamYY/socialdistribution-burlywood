import base64
import uuid
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from core.models import Author
from entries.models import Entry
from interactions.models import Comment

# Create your tests here.

"""
Creates a series of tests for all the user stories relating to the author endpoint
"""
class AuthorEndpointTest(APITestCase):
    """
    Test to ensure all ID's are unique by attempting to create one that is not unique
    User story #2
    """
    def test_consistent_ids(self):
        firstauthorURL = reverse("ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_200_OK)
        secondauthorURL = reverse("ApiAuthor",kwargs = {"id":2})
        # Attempts to create an author with the wrong ID for it's location
        author2 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Daltonssda","github": "http://g.com","profileImage": "https://scaled.jpg","web": "http://localhost:8000/app/authors/2" }
        put2 = self.client.put(secondauthorURL,author2,format = "json")
        self.assertEqual(put2.status_code,status.HTTP_400_BAD_REQUEST)
        # Tests overwritting a user with the same ID
        author3 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Author3","github": "http://3.com","profileImage": "https://scaleded.jpg","web": "http://localhost:8000/app/authors/1" }
        put3 = self.client.put(firstauthorURL,author3,format = "json") # Should replace author 1 ensuring that there is no repeated ID's
        self.assertEqual(put3.status_code,status.HTTP_200_OK) # Ensures that it worked
        self.assertEqual(Author.objects.count(),1) # Ensures there is only one author still there
        author = Author.objects.get(id = 1)
        # Ensures all the values match that of author 3 instead of author 1
        self.assertEqual(author.id,1)
        self.assertEqual(author.username,"Author3")
        self.assertEqual(author.github, "http://3.com")
        self.assertEqual(author.picture,"https://scaleded.jpg")
    
    """
    Test to ensure node can handle multiple users
    User story #3
    """
    def test_multiple_authors(self):
        # Adds the first author
        firstauthorURL = reverse("ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_200_OK) # Ensures the first author was added successfully
        # Adds the second author
        secondauthorURL = reverse("ApiAuthor",kwargs = {"id": 2})
        author2 = {"type":"author","id":secondauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Low","github": "http://github.com/daltons","profileImage": "https://image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/2" }
        put2 = self.client.put(secondauthorURL,author2,format = "json")
        self.assertEqual(put2.status_code,status.HTTP_200_OK) # Ensures the first author was added successfully
        self.assertEqual(Author.objects.count(),2) # Ensures that both are in the database
        author1 = Author.objects.get(id = 1)
        author2 = Author.objects.get(id = 2)
        # Checks both display names to see that the values have been properly added
        self.assertEqual(author1.username,"Dalton")
        self.assertEqual(author2.username,"Low")

    """
    Tests getting the authors profile page
    User story #4
    """
    def test_author_page(self):
        # Adds an author whos page we will get
        firstauthorURL = reverse("ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_200_OK) # Ensures the first author was added successfully
        get1 = self.client.get(firstauthorURL,format = "json")
        self.assertEqual(get1.data,author1) # Ensures that the data from the author matches what we get from their page

"""
Creates a test for the authors endpoint
"""
class AuthorsEndpointTest(APITestCase):
    def test_get_multiple_authors(self):
        # Adds the first author
        firstauthorURL = reverse("ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_200_OK) # Ensures the first author was added successfully
        # Adds the second author
        secondauthorURL = reverse("ApiAuthor",kwargs = {"id": 2})
        author2 = {"type":"author","id":secondauthorURL[:-1],"host":"/api/","displayName":"Low","github": "http://github.com/daltons","profileImage": "https://image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/2" }
        put2 = self.client.put(secondauthorURL,author2,format = "json")
        self.assertEqual(put2.status_code,status.HTTP_200_OK) # Ensures the first author was added successfully
        # Checks that the authors page properly retrives them
        multiauthorURL = reverse("ApiAuthors")
        get1 = self.client.get(multiauthorURL,format = "json")
        self.assertEqual(get1.data,{"type":"authors","authors": [author1,author2]})


AuthorModel = Entry._meta.get_field('author').related_model

class EntryAPITest(APITestCase):
    """
    Creates a series of tests for all the entry API endpoints.
    """
    def setUp(self):
        """
        Initialize some mock data for testing.
        """
        AuthorModel = Entry._meta.get_field('author').related_model

        # Create a dummy author with the basic fields
        self.author = AuthorModel.objects.create(
            id=1,
            username="test_author_1",
            name="Test Author 1",
            github="http://github.com/testauthor"
        )

        # Create a valid, tiny 1x1 pixel PNG in base64 format
        self.tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Save it to the database
        self.image_entry = Entry.objects.create(
            id=uuid.uuid4(),
            author=self.author,
            title="Test Image Entry with PNG",
            contentType="image/png;base64",
            content=f"data:image/png;base64,{self.tiny_png_b64}",
            visibility="PUBLIC"
        )
    
    def test_create_entry(self):
        """
        User Story #10: As an author, I want to make entries.

        Verifie POST to /authors/{id}/entries/ creates a record and returns an FQID.
        """
        url = reverse("ApiEntries", kwargs={"author_id": self.author.id})
        data = {
            "title": "API Created Entry",
            "description": "Testing",
            "contentType": "text/plain",
            "content": "Hello World",
            "visibility": "PUBLIC",
        }
        response = self.client.post(url, data, format="json")

        # Check if the entry was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if it's a URL and contains 'authors' and the ID (FQID)
        self.assertIn("/authors/", response.data["id"])

        # Check if the entry exists
        self.assertTrue(Entry.objects.filter(title="API Created Entry").exists())
    
    def test_get_single_entry(self):
        """
        Verify GET to /authors/{id}/entries/{eid}/ returns correct structure.
        """
        entry = Entry.objects.create(author=self.author, title="Fetch Me", visibility="PUBLIC")
        url = reverse("ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "entry")
        self.assertIn("comments", response.data)
        self.assertIn("likes", response.data)
        self.assertIn("author", response.data)
    
    def test_edit_entry(self):
        """
        User Story #12: As an author, I want to edit my entries locally.

        Verify PUT to /authors/{uid}/entries/{entry_id}/ updates the data.
        """
        entry = Entry.objects.create(
            author=self.author,
            title="Old Title",
            contentType="text/plain",
            content="Original content",
            visibility="PUBLIC",
        )
        url = reverse("ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})

        # Log in as the author
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()
        
        update_data = {"title": "New Title", "content": "Updated content"}
        response = self.client.put(url, update_data, format="json")
        
        # Check if the response is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry.refresh_from_db()

        # Check if the entry was updated correctly
        self.assertEqual(entry.title, "New Title")
        self.assertEqual(entry.content, "Updated content")
        self.assertEqual(entry.author_id, self.author.id)

    def test_delete_entry(self):
        """
        User Story #17: As an author, I want to delete my own entries locally.

        Verify DELETE sets visibility to DELETED and makes it 404 in API.
        """
        entry = Entry.objects.create(author=self.author, title="Delete Me", visibility="PUBLIC")
        url = reverse("ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})

        # Log in as the author
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()

        response = self.client.delete(url)

        # Check if the delete request was successful
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if it's only soft-deleted
        self.assertTrue(Entry.objects.filter(id=entry.id).exists())

        entry.refresh_from_db()

        # Check if the visibility is set properly
        self.assertEqual(entry.visibility, "DELETED")
        
        # Check if it's no longer accessible via a GET request
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_image_entry(self):
        """
        User Story #16: As an author, entries I create can be images.

        Verify GET to image api returns the raw image with correct MIME type.
        Return 404 if not an image entry.

        URL: ://service/api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image
             ://service/api/entries/{ENTRY_FQID}/image
        """
        url = reverse("ApiEntryImage", kwargs={
            "author_id": self.author.id,
            "entry_id": self.image_entry.id
        })
        response = self.client.get(url)

        # Check if the response is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if returned the exact MIME type (image/png) instead of JSON
        self.assertEqual(response["Content-Type"], "image/png")

        # Check if the image was decoded into raw binary bytes
        expected_binary = base64.b64decode(self.tiny_png_b64)
        self.assertEqual(response.content, expected_binary)

        # Check if 404 for non-image entry
        text_entry = Entry.objects.create(
            author=self.author,
            title="Text Post",
            contentType="text/plain",
            content="Just words.",
            visibility="PUBLIC",
        )
        text_image_url = reverse("ApiEntryImage", kwargs={
            "author_id": self.author.id,
            "entry_id": text_entry.id
        })
        text_response = self.client.get(text_image_url)
        self.assertEqual(text_response.status_code, status.HTTP_404_NOT_FOUND)

        # Global image endpoint
        global_url = reverse("ApiEntryImageGlobal", kwargs={"entry_id": self.image_entry.id})
        global_response = self.client.get(global_url)

        # Check the response and MIME type
        self.assertEqual(global_response.status_code, status.HTTP_200_OK)
        self.assertTrue(global_response["Content-Type"].startswith("image/png"))

    def test_get_entries_pagination(self):
        """
        Verify GET to /authors/{id}/entries/ returns paginated entries.
        """
        # Create multiple entries
        for i in range(10):
            Entry.objects.create(author=self.author, title=f"Post {i}", visibility="PUBLIC")
            
        url = reverse("ApiEntries", kwargs={"author_id": self.author.id})
        
        # Request page 2 with size 3
        response = self.client.get(url, {"page": 2, "size": 3})
        
        # Check if the response is successful and has correct pagination structures
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("type"), "entries")
        self.assertEqual(response.data.get("page_number"), 2)
        self.assertEqual(response.data.get("size"), 3)

        self.assertIn("src", response.data)
        self.assertEqual(len(response.data["src"]), 3)

class CommentApiTest(TestCase):
    """
    Tests for all comment-related API endpoints.
    """
    def setUp(self):
        self.author = Author.objects.create(name="Tester")

        self.entry = Entry.objects.create(
            author=self.author,
            title="Test Entry",
            content="Hello world",
            visibility="PUBLIC"
        )

        self.entry_url = f"http://testserver/app/entry/{self.entry.id}/"

    """
    As an author, I want to comment on entries that I can access,
    so I can make a witty reply.
    """
    def test_author_can_post_comment(self):
        response = self.client.post(
            f"/api/authors/{self.author.id}/entries/{self.entry.id}/comments/add/",
            data={
                "author": f"http://testserver/authors/{self.author.id}",
                "comment": "Nice post!"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)

    """
    As an author, when someone sends me an entry,
    I want to see the comments so I can read feedback.
    """
    def test_get_comments_on_entry(self):
        Comment.objects.create(
            id="http://testserver/comments/1",
            author="http://testserver/authors/1",
            entry=self.entry_url,
            comment="Hello"
        )

        response = self.client.get(
            f"/api/authors/{self.author.id}/entries/{self.entry.id}/comments/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    """
    As an author, comments should follow the spec format
    so that other nodes can understand them.
    """
    def test_comment_serializer_fields(self):
        Comment.objects.create(
            id="http://testserver/comments/2",
            author="http://testserver/authors/1",
            entry=self.entry_url,
            comment="Check fields"
        )

        response = self.client.get(
            f"/api/authors/{self.author.id}/entries/{self.entry.id}/comments/"
        )

        comment_data = response.data["src"][0]

        self.assertIn("type", comment_data)
        self.assertIn("author", comment_data)
        self.assertIn("comment", comment_data)
        self.assertIn("published", comment_data)

    """
    As an author, I should not be able to comment on entries that do not exist.
    """
    def test_comment_on_missing_entry_fails(self):
        response = self.client.post(
            f"/api/authors/{self.author.id}/entries/99999999-9999-9999-9999-999999999999/comments/add/",
            data={
                "author": f"http://testserver/authors/{self.author.id}",
                "comment": "Invalid"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)