from urllib import response

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.shortcuts import render
from rest_framework import status
from rest_framework.test import APITestCase
from .serializers import LikeSerializer, AuthorSerializer
from core.admin import AuthorAdmin, AuthorRequestAdmin
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.admin.sites import AdminSite
import base64
import uuid
from core.models import Author, AuthorRequest
from entries.models import Entry
from interactions.models import Comment, Like
from core.views import SignUpProcessing

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
        firstauthorURL = reverse("api:ApiAuthor",kwargs = {"id": 1})
        # Creates an author outright to avoid having to accept a request
        author1 = Author(id = 1,host="http://localhost:8000/api/",name="Dalton",username = "Dalton",github= "http://github.com/dalton")
        author1.save()
        secondauthorURL = reverse("api:ApiAuthor",kwargs = {"id":2})
        # Attempts to create an author with the wrong ID for it's location
        author2 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Daltonssda","github": "http://g.com","profileImage": "","web": "http://localhost:8000/app/authors/2" }
        put2 = self.client.put(secondauthorURL,author2,format = "json")
        self.assertEqual(put2.status_code,status.HTTP_400_BAD_REQUEST)
        # Tests overwritting a user with the same ID
        author3 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Author3","github": "http://3.com","profileImage": "","web": "http://localhost:8000/app/authors/1" }
        put3 = self.client.put(firstauthorURL,author3,format = "json") # Should replace author 1 ensuring that there is no repeated ID's
        self.assertEqual(put3.status_code,status.HTTP_200_OK) # Ensures that it worked
        self.assertEqual(Author.objects.count(),1) # Ensures there is only one author still there
        # Ensures all the values match that of author 3 instead of author 1
        author = Author.objects.get()
        self.assertEqual(author.id,1)
        self.assertEqual(author.name,"Author3")
        self.assertEqual(author.github, "http://3.com")
    
    """
    Test to ensure node can handle multiple users
    User story #3
    """
    def test_multiple_authors(self):
        # Adds the first author
        firstauthorURL = reverse("api:ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_201_CREATED) # Ensures the first author was added successfully
        # Adds the second author
        secondauthorURL = reverse("api:ApiAuthor",kwargs = {"id": 2})
        author2 = {"type":"author","id":secondauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Low","github": "http://github.com/daltons","profileImage": "https://image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/2" }
        put2 = self.client.put(secondauthorURL,author2,format = "json")
        self.assertEqual(put2.status_code,status.HTTP_201_CREATED) # Ensures the first author was added successfully
        self.assertEqual(AuthorRequest.objects.count(),2) # Ensures that both are in the database
        # Checks that the two author requests were created
        author1 = AuthorRequest.objects.get(id = 1)
        author2 = AuthorRequest.objects.get(id = 2)
        # Checks both display names to see that the values have been properly added
        self.assertEqual(author1.name,"Dalton")
        self.assertEqual(author2.name,"Low")

    """
    Tests confirming a author request
    User Story 67
    """
    def test_confirm_author_request(self):
        # Adds an author
        firstauthorURL = reverse("api:ApiAuthor",kwargs = {"id": 1})
        author1 = {"type":"author","id":firstauthorURL[:-1],"host":"http://localhost:8000/api/","displayName":"Dalton","github": "http://github.com/dalton","profileImage": "https://www.bigfootdigital.co.uk/wp-content/uploads/2020/07/image-optimisation-scaled.jpg","web": "http://localhost:8000/app/authors/1" }
        put1 = self.client.put(firstauthorURL,author1,format = "json")
        self.assertEqual(put1.status_code,status.HTTP_201_CREATED) # Ensures the first author was added successfully
        self.assertEqual(AuthorRequest.objects.count(),1) # Checks that it made an author request object
        # Creates an instance of the AuthorRequestAdmin
        admin = AuthorRequestAdmin(AuthorRequest, AdminSite())
        # Gets the author requests
        authorRequests = AuthorRequest.objects.all()
        # Passes an empty request along with the list of author requests (Should be just the one created earlier)
        admin.approve(RequestFactory(), authorRequests)
        self.assertEqual(AuthorRequest.objects.count(),0) # Checks that the author request is gone
        self.assertEqual(Author.objects.count(),1) # Checks that it made an author object
        author = Author.objects.get()
        # Checks to ensure the newly created APIAuthor has matching values to our request
        self.assertEqual(author.id,1)
        self.assertEqual(author.name,"Dalton")
        self.assertEqual(author.host,"http://localhost:8000/api/")

    """
    Tests getting the authors profile page
    User story #4
    """
    def test_author_page(self):
        # Adds an author whos page we will get
        firstauthorURL = reverse("api:ApiAuthor",kwargs = {"id": 1})
        # Creates an author outright to avoid having to accept a request
        author1 = Author(id = 1,host="http://localhost:8000/api/",name="Dalton",username = "Dalton",github= "http://github.com/dalton")
        author1.save()
        # Runs the get to get the page
        get1 = self.client.get(firstauthorURL,format = "json")
        self.assertEqual(get1.data,AuthorSerializer(author1).data) # Ensures that the data from the author matches what we get from their page

"""
Creates a test for the authors endpoint
"""
class AuthorsEndpointTest(APITestCase):
    def test_get_multiple_authors(self):
        # Creates the first author outright to avoid having to accept a request
        author1 = Author(id = 1,host="http://localhost:8000/api/",name="Dalton",username = "Dalton",github= "http://github.com/dalton")
        author1.save()
        # Creates the second author outright to avoid having to accept a request
        author2 = Author(id = 2,host="http://localhost:8000/api/",name="DaltonSS",username = "DaltonU",github= "http://github.com/dalton")
        author2.save()
        # Checks that the authors page properly retrives them
        multiauthorURL = reverse("api:ApiAuthors")
        get1 = self.client.get(multiauthorURL,format = "json")
        self.assertEqual(get1.data,{"type":"authors","authors": [AuthorSerializer(author1).data,AuthorSerializer(author2).data]})

"""
Creates a test for the author and entry likes endpoint
"""
class AuthorEntryLikeEndpointTest(APITestCase):
    def test_author_entry_get_likes(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/" ,web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.save()
        # Gets the info from the website
        like_url = reverse("api:ApiAuthorAndEntryLikes",kwargs = {"author_id":author1.id,"entry_id":entry1.id})

        get1 = self.client.get(like_url,format="json")
        # Ensures there is exactly one like
        self.assertEqual(get1.data["count"],1)
        like = get1.data["src"][0]
        # Ensure the like has the correct entry
        self.assertEqual(like["object"].split("/")[-1],str(entry1.id))
        author = like["author"]
        self.assertEqual(author["displayName"],author2.name)

    def test_author_entry_get_likes_pagination(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/" ,web = "/app/authors/2")
        author2.save()
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author1_fqid = f"{author1.host}authors/{author1.id}"
        author2_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author1_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"{author1_fqid}/liked/{like1.uuid}"
        like1.save()
        like2 = Like(object = object_fqid, author = author2_fqid)
        like2.uuid = uuid.uuid4()
        like2.id = f"{author2_fqid}/liked/{like2.uuid}"
        like2.save()
        # Gets the info from the website
        like_url = f"{reverse("api:ApiAuthorAndEntryLikes",kwargs = {"author_id":author1.id,"entry_id":entry1.id})}?page_number=1&size=1"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],1)
        self.assertEqual(get1.data["count"],2)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 1)
        author = likes[0]["author"]
        self.assertEqual(author["id"], author2_fqid)

        like_url = f"{reverse("api:ApiAuthorAndEntryLikes",kwargs = {"author_id":author1.id,"entry_id":entry1.id})}?page_number=0&size=0"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],5)

        like_url = f"{reverse("api:ApiAuthorAndEntryLikes",kwargs = {"author_id":author1.id,"entry_id":entry1.id})}?page_number=500&size=5"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],500)
        self.assertEqual(get1.data["size"],5)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 0)

"""
Creates a test for the entry ikes endpoint
"""
class EntryLikeEndpointTest(APITestCase):
    def test_entry_get_likes(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.save()
        # Gets the info from the website
        like_url = reverse("api:ApiEntryLikes",kwargs = {"entry_fqid":object_fqid})
        get1 = self.client.get(like_url,format="json")
        # Ensures there is exactly one like
        self.assertEqual(get1.data["count"],1)
        like = get1.data["src"][0]
        # Ensure the like has the correct entry
        self.assertEqual(like["object"].split("/")[-1],str(entry1.id))
        author = like["author"]
        self.assertEqual(author["displayName"],author2.name)

    def test_entry_get_likes_pagination(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/" ,web = "/app/authors/2")
        author2.save()
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author1_fqid = f"{author1.host}authors/{author1.id}"
        author2_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author1_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"{author1_fqid}/liked/{like1.uuid}"
        like1.save()
        like2 = Like(object = object_fqid, author = author2_fqid)
        like2.uuid = uuid.uuid4()
        like2.id = f"{author2_fqid}/liked/{like2.uuid}"
        like2.save()
        # Gets the info from the website
        like_url = f"{reverse("api:ApiEntryLikes",kwargs = {"entry_fqid":object_fqid})}?page_number=1&size=1"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],1)
        self.assertEqual(get1.data["count"],2)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 1)
        author = likes[0]["author"]
        self.assertEqual(author["id"], author2_fqid)

        like_url = f"{reverse("api:ApiEntryLikes",kwargs = {"entry_fqid":object_fqid})}?page_number=0&size=0"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],5)

        like_url = f"{reverse("api:ApiEntryLikes",kwargs = {"entry_fqid":object_fqid})}?page_number=500&size=5"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],500)
        self.assertEqual(get1.data["size"],5)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 0)

"""
Allows the user to create a like
"""
class AddLikeEndpointTest(APITestCase):
    """
    Tests sending a like to a user
    User Story # 58
    """
    def test_sending_like(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)

        like1 = LikeSerializer(like1)

        # Gets the info from the website
        like_url = reverse("api:ApiSendLike",kwargs = {"author_id":author1.id})
        post1 = self.client.post(like_url,like1.data,format = 'json')
        # Ensures there is one like in the data base
        self.assertEqual(Like.objects.count(),1)
        # Ensures it matches with the like object information
        self.assertEqual(Like.objects.get().author,author_fqid)
        self.assertEqual(Like.objects.get().object,object_fqid)

class ApiAuthorLikedTest(APITestCase):
    def test_get_author_like(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"{author_fqid}/liked/{like1.uuid}"
        like1.save()

        like_id = f"{author_fqid}/liked/{like1.uuid}"

        # Gets the info from the website
        like_url = reverse("api:ApiAuthorLiked",kwargs = {"author_id":author2.id})
        get1 = self.client.get(like_url,format="json")
        # Ensures there is one like in the data base
        self.assertEqual(Like.objects.count(),1)
        # Ensures it matches with the like object information
        self.assertEqual(get1.data["type"], "likes")
        self.assertEqual(get1.data["id"], f"http://testserver{like_url}")
        self.assertEqual(get1.data["src"][0]["type"], "like")
        self.assertEqual(get1.data["src"][0]["author"]["id"], author_fqid)
        self.assertEqual(get1.data["src"][0]["id"], like1.id)
        self.assertEqual(get1.data["src"][0]["object"], object_fqid)

    def test_get_author_like_pagination(self):
        # Creates two users, one to make the entry and one to like it
        author = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author)
        entry1.save()
        entry2 = Entry(title = "B",author = author)
        entry2.save()

        object1_fqid = f"{author.host}authors/{author.id}/entries/{entry1.id}"
        author_fqid = f"{author.host}authors/{author.id}"
        like1 = Like(object = object1_fqid, author = author_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"{author_fqid}/liked/{like1.uuid}"
        like1.save()

        object2_fqid = f"{author.host}authors/{author.id}/entries/{entry2.id}"
        like2 = Like(object = object2_fqid, author = author_fqid)
        like2.uuid = uuid.uuid4()
        like2.id = f"{author_fqid}/liked/{like2.uuid}"
        like2.save()
        
        like2_id = f"{author_fqid}/liked/{like2.uuid}"

        # Gets the info from the website
        like_url = f"{reverse("api:ApiAuthorLiked",kwargs = {"author_id":author.id})}?page_number=1&size=1"

        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],1)
        self.assertEqual(get1.data["count"],2)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 1)
        object = likes[0]["object"]
        self.assertEqual(object, object2_fqid)
        id = likes[0]["id"]
        self.assertEqual(id, like2_id)

        like_url = f"{reverse("api:ApiAuthorLiked",kwargs = {"author_id":author.id})}?page_number=0&size=0"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],5)

        like_url = f"{reverse("api:ApiAuthorLiked",kwargs = {"author_id":author.id})}?page_number=500&size=5"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],500)
        self.assertEqual(get1.data["size"],5)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 0)
        
class ApiSingleLikeRemoteLocalTest(APITestCase):
    def test_get_single_like_remote_local(self):
         # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"http://testserver/api/authors/{author2.id}/liked/{like1.uuid}"
        like1.save()

        author_fqid = f"{author2.host}authors/{author2.id}"
        like_url = reverse("api:ApiSingleLikeRemoteLocal",kwargs = {"author_id":author2.id, "like_id": like1.uuid})
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["type"], "like")
        self.assertEqual(get1.data["author"]["id"], author_fqid)
        self.assertEqual(get1.data["id"], f"http://testserver{like_url}")
        self.assertEqual(get1.data["object"], object_fqid)

class ApiAuthorLikedLocalTest(APITestCase):
    def get_author_liked_local(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.uuid = uuid.uuid4()
        like1.id = f"http://testserver/api/authors/{author2.id}/liked/{like1.uuid}"
        like1.save()

        like_id = f"{author_fqid}/liked/{like1.id}"

        like_url = reverse("api:ApiAuthorLikedLocal",kwargs = {"author_fqid":author_fqid})
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["type"], "likes")
        self.assertEqual(get1.data["id"], f"http://testserver{like_url}")
        self.assertEqual(get1.data["src"][0]["type"], "like")
        self.assertEqual(get1.data["src"][0]["author"]["id"], author_fqid)
        self.assertEqual(get1.data["src"][0]["id"], like_id)
        self.assertEqual(get1.data["src"][0]["object"], object_fqid)

    def get_author_liked_local_pagination(self):
        # Creates two users, one to make the entry and one to like it
        author = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author)
        entry1.save()
        entry2 = Entry(title = "B",author = author)
        entry2.save()

        object1_fqid = f"{author.host}authors/{author.id}/entries/{entry1.id}"
        author_fqid = f"{author.host}authors/{author.id}"
        like1 = Like(object = object1_fqid, author = author_fqid)
        like1.save()

        object2_fqid = f"{author.host}authors/{author.id}/entries/{entry2.id}"
        like2 = Like(object = object2_fqid, author = author_fqid)
        like2.save()

        like1_id = f"{author_fqid}/liked/{like1.id}"

        # Gets the info from the website
        like_url = f"{reverse("api:ApiAuthorLikedLocal",kwargs = {"author_fqid":author_fqid})}?page_number=1&size=1"

        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],1)
        self.assertEqual(get1.data["count"],2)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 1)
        object = likes[0]["object"]
        self.assertEqual(object, object2_fqid)
        id = likes[0]["id"]
        self.assertEqual(id, like1_id)

        like_url = f"{reverse("api:ApiAuthorLikedLocal",kwargs = {"author_fqid":author_fqid})}?page_number=0&size=0"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],1)
        self.assertEqual(get1.data["size"],5)

        like_url = f"{reverse("api:ApiAuthorLikedLocal",kwargs = {"author_fqid":author_fqid})}?page_number=500&size=5"
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["page_number"],500)
        self.assertEqual(get1.data["size"],5)
        likes = get1.data["src"]
        self.assertEqual(len(likes), 0)

class ApiSingleLikeLocalTest(APITestCase):
    def get_single_like(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "http://testserver/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "http://testserver/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be liked
        entry1 = Entry(title = "A",author = author1)
        entry1.save()

        object_fqid = f"{author1.host}authors/{author1.id}/entries/{entry1.id}"
        author_fqid = f"{author2.host}authors/{author2.id}"
        like1 = Like(object = object_fqid, author = author_fqid)
        like1.save()

        like_id = f"{author_fqid}/liked/{like1.id}"

        like_url = reverse("api:ApiSingleLikeLocal",kwargs = {"like_url":like_id})
        get1 = self.client.get(like_url,format="json")
        self.assertEqual(get1.data["type"], "like")
        self.assertEqual(get1.data["author"]["id"], author_fqid)
        self.assertEqual(get1.data["id"], like_id)
        self.assertEqual(get1.data["object"], object_fqid)

"""
Tests admin using priviledges
User Story 66
"""
class AdminPanelAbilityTest(TestCase):
    """
    Tests adding a user
    Part of User story 66
    """
    def test_add_user_admin(self):
        # Gets the link to add a user
        adminLink = reverse("admin:core_author_add")
        # Opens up the admin panel
        client = Client()
        adminUser = User.objects.create_superuser(username="1",password="2")
        adminUser.save()
        client.login(username =  "1", password = "2")
        # Makes a hashed password for the post request
        password = make_password("123")
        # Posts the user
        client.post(adminLink,{"username":"Doug","password":password,"name":"Doug","description": "This is a test","picture": "","github": "","followers":[],"host":"http://localhost:8000/api/","web":"http://localhost:8000/app/authors/1","_save":"Save"})
        # Ensures there is an author created
        self.assertEqual(Author.objects.count(),1)
        # Checks that the authors information matches
        self.assertEqual(Author.objects.get().username,"Doug")
        self.assertEqual(Author.objects.get().description,"This is a test")
    """
    Tests updating a user
    Part of User story 66
    """
    def test_edit_user_admin(self):
        # Creates initial author
        author = Author(username = "a",password = "b",name = "c",description = "d",host = "/api/",web = "/app/authors/1")
        author.save()
        # Gets the link to change an author
        adminLink = reverse("admin:core_author_change",kwargs = {"object_id":author.id})
        # Opens up the admin panel
        client = Client()
        adminUser = User.objects.create_superuser(username="1",password="2")
        adminUser.save()
        client.login(username =  "1", password = "2")
        # Makes a hashed password for the post request
        password = make_password("123")
        # Posts the user
        client.post(adminLink,{"username":"Doug","password":password,"name":"Doug","description": "This is a test","picture": "","github": "","followers":[],"host":"http://localhost:8000/api/","web":"http://localhost:8000/app/authors/1","_save":"Save"})
        # Ensures there is an author created
        self.assertEqual(Author.objects.count(),1)
        # Checks that the authors information matches
        self.assertEqual(Author.objects.get().username,"Doug")
        self.assertEqual(Author.objects.get().description,"This is a test")
    """
    Tests deleting a user
    Part of User story 66
    """
    def test_delete_user_admin(self):
        # Creates initial author
        author = Author(username = "a",password = "b",name = "c",description = "d",host = "/api/",web = "/app/authors/1")
        author.save()
        # Gets the link to change an author
        adminLink = reverse("admin:core_author_delete",kwargs = {"object_id":author.id})
        # Opens up the admin panel
        client = Client()
        adminUser = User.objects.create_superuser(username="1",password="2")
        adminUser.save()
        client.login(username =  "1", password = "2")
        # Posts the delete
        client.post(adminLink,{"_save": "Save"})
        # Ensures there is no more author
        self.assertEqual(Author.objects.count(),0)

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

        # Log in as the author
        session = self.client.session
        session["author_id"] = self.author.id
        session.save()
    
    def test_create_entry(self):
        """
        User Story #10: As an author, I want to make entries.

        Verifie POST to /authors/{id}/entries/ creates a record and returns an FQID.
        """
        url = reverse("api:ApiEntries", kwargs={"author_id": self.author.id})
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
        url = reverse("api:ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})
        
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
        url = reverse("api:ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})

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
        url = reverse("api:ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})

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
        url = reverse("api:ApiEntryImage", kwargs={
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
        text_image_url = reverse("api:ApiEntryImage", kwargs={
            "author_id": self.author.id,
            "entry_id": text_entry.id
        })
        text_response = self.client.get(text_image_url)
        self.assertEqual(text_response.status_code, 404)

        # Global image endpoint
        entry_fqid = f"http://testserver/api/authors/{self.author.id}/entries/{self.image_entry.id}"
        global_url = reverse("api:ApiEntryImageGlobal", kwargs={"entry_fqid": entry_fqid})
        global_response = self.client.get(global_url)

        # Check the response and MIME type
        self.assertEqual(global_response.status_code, status.HTTP_200_OK)
        self.assertTrue(global_response["Content-Type"].startswith("image/png"))
    
    def test_get_image_via_fqid_path(self):
        """
        Verify the proxy logic handles a full URL path in the entry_fqid.
        """
        # Construct a local FQID
        fqid = f"http://testserver/api/authors/{self.author.id}/entries/{self.image_entry.id}"

        # Request via the Global Proxy URL pattern: /api/entries/<path:entry_fqid>/image
        url = reverse('api:ApiEntryImageGlobal', kwargs={'entry_fqid': fqid})
        
        response = self.client.get(url)
        
        # Should resolve locally and return binary data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, base64.b64decode(self.tiny_png_b64))

    def test_markdown_entry_can_reference_hosted_image_url(self):
        """
        US #65: Verify the markdown entry can reference a hosted image on node
        """
        image_url = f"/api/authors/{self.author.id}/entries/{self.image_entry.id}/image"
        markdown_source = f"## Image from entry\n![alt 123]({image_url})"

        url = reverse("api:ApiEntries", kwargs={"author_id": self.author.id})
        response = self.client.post(url, {
            "title": "Markdown With Hosted Image",
            "description": "Testing hosted image reference",
            "contentType": "text/markdown",
            "content": markdown_source,
            "visibility": "PUBLIC",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created = Entry.objects.get(title="Markdown With Hosted Image")
        self.assertEqual(created.contentType, "text/markdown")
        self.assertEqual(created.content, markdown_source)

        # Check if the referenced URL is actually a valid hosted image resource
        image_response = self.client.get(image_url)
        self.assertEqual(image_response.status_code, status.HTTP_200_OK)
        self.assertTrue(image_response["Content-Type"].startswith("image/"))
        
    def test_proxy_404_on_invalid_fqid(self):
        """
        Ensure it returns 404 if the FQID refers to a non-existent local entry.
        """
        bad_fqid = "http://testserver/api/authors/1/entries/00000000-0000-0000-0000-000000000000"
        url = reverse('api:ApiEntryImageGlobal', kwargs={'entry_fqid': bad_fqid})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_entries_pagination(self):
        """
        Verify GET to /authors/{id}/entries/ returns paginated entries.
        """
        # Create multiple entries
        for i in range(10):
            Entry.objects.create(author=self.author, title=f"Post {i}", visibility="PUBLIC")
            
        url = reverse("api:ApiEntries", kwargs={"author_id": self.author.id})
        
        # Request page 2 with size 3
        response = self.client.get(url, {"page": 2, "size": 3})
        
        # Check if the response is successful and has correct pagination structures
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("type"), "entries")
        self.assertEqual(response.data.get("page_number"), 2)
        self.assertEqual(response.data.get("size"), 3)

        self.assertIn("src", response.data)
        self.assertEqual(len(response.data["src"]), 3)

    def test_get_deleted_entry(self):
        """
        US #78: As a node admin, I want deleted entries stay in the database and only be removed from the UI and API, so I can see what was deleted.
        """
        entry = Entry.objects.create(author=self.author, title="Delete Me", visibility="PUBLIC")
        entry_url1 = reverse("api:ApiEntry", kwargs={"author_id": self.author.id, "entry_id": entry.id})
        entry_url2 = reverse("api:ApiEntries", kwargs={"author_id": self.author.id})
        entry_url3 = reverse("api:browse_public_entries")

        # Log in as the author
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()
        self.client.delete(entry_url1)
        
        response1 = self.client.get(entry_url1)
        self.assertEqual(response1.status_code, 404)

        # only the image entry should remain since it was not deleted
        response2 = self.client.get(entry_url2)
        self.assertEqual(response2.data["count"], 1)
        self.assertEqual(len(response2.data["src"]), 1)
        self.assertNotIn(str(entry.id), response2.data["src"][0]["id"])

        response3 = self.client.get(entry_url3)
        self.assertEqual(response3.data["count"], 1)
        self.assertEqual(len(response3.data["src"]), 1)
        self.assertNotIn(str(entry.id), response2.data["src"][0]["id"])

        # entry is still in the database
        self.assertTrue(Entry.objects.filter(id = entry.id).exists())

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

        self.entry_url = f"http://testserver/api/authors/{self.author.id}/entries/{self.entry.id}/"

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
            f"/api/authors/{self.author.id}/entries/{self.entry.id}/comments"
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
            f"/api/authors/{self.author.id}/entries/{self.entry.id}/comments"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["src"]), 1)

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

class VisibilityAPITest(TestCase):
    """
    Create a series of tests for visibilities of entry API endpoints.
    """
    def setUp(self):
        # Create Author A and Author B
        self.author_a = Author.objects.create(username="A", name="AA")
        self.author_b = Author.objects.create(username="B", name="BB")
        
        # Create different types of entries of Author A
        self.private_entry = Entry.objects.create(
            author=self.author_a,
            title="A's Secret",
            content="Top Secret",
            visibility="FRIENDS"
        )
        
        self.public_entry = Entry.objects.create(
            author=self.author_a,
            title="A's Entry Bus",
            content="No More Secretes",
            visibility="UNLISTED"
        )

        self.tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="        
        self.private_image_entry = Entry.objects.create(
            id=uuid.uuid4(),
            author=self.author_a,
            title="Test Image Entry with PNG",
            contentType="image/png;base64",
            content=f"data:image/png;base64,{self.tiny_png_b64}",
            visibility="FRIENDS"
        )
    
    def test_api_public_access(self):
        """
        Verify the access to public or unlist entries.
        """
        # Log in as B
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        # Try to access A's unlisted entry via API
        url = reverse('api:ApiEntry', kwargs={'author_id': self.author_a.id, 'entry_id': self.public_entry.id})
        response = self.client.get(url)

        # Check if the status code is 200 OK
        self.assertEqual(response.status_code, 200)

    def test_api_entry_visibility(self):
        """
        Verify the access to friends only entry.
        """
        # Log in as B
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        # Try to access A's private entry via API
        url = reverse('api:ApiEntry', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        
        # Check if the status code is 403 Forbidden
        self.assertEqual(response.status_code, 403)

        # Make B a friend of A (Mutual Follow)
        self.author_a.followers.add(self.author_b)
        self.author_b.followers.add(self.author_a)

        url = reverse('api:ApiEntry', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        
        # Check if the status code is 200 OK
        self.assertEqual(response.status_code, 200)
        
    def test_api_image_visibility(self):
        """
        Verify the access to friends only image entry.
        """
        # Log in as B
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        url = reverse('api:ApiEntryImage', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_image_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Make B a friend of A (Mutual Follow)
        self.author_a.followers.add(self.author_b)
        self.author_b.followers.add(self.author_a)

        url = reverse('api:ApiEntryImage', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_image_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_api_comments_visibility(self):
        """
        Verify the access to comments on a friends only entry.
        """
        # Set up the private entry with a comment
        base_url = "http://testserver"
        entry_url = f"{base_url}/app/entry/{self.private_entry.id}/"
        Comment.objects.create(
            id=f"{base_url}/comments/test-uuid",
            author=f"{base_url}/authors/{self.author_a.id}",
            entry=entry_url,
            comment="Secret comment"
        )

        # Log in as B
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        url = reverse('api:ApiEntryComments', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Make B a friend of A (Mutual Follow)
        self.author_a.followers.add(self.author_b)
        self.author_b.followers.add(self.author_a)

        url = reverse('api:ApiEntryComments', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_api_entry_likes_visibility(self):
        """
        Verify the access to likes on a friends only entry.
        """
        base_url = "http://testserver"
        entry_url = f"{base_url}/app/entry/{self.private_entry.id}/"
    
        Like.objects.create(
            author=f"http://testserver/api/authors/{self.author_a.id}",
            object=entry_url
        )

        # Log in as B
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        url = reverse('api:ApiAuthorAndEntryLikes', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Make B a friend of A (Mutual Follow)
        self.author_a.followers.add(self.author_b)
        self.author_b.followers.add(self.author_a)

        url = reverse('api:ApiAuthorAndEntryLikes', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_entry.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_api_liked_history_visibility(self):
        """
        Verify the access to liked history for friends only entries.
        """
        # Setup B likes A's private entry
        entry_url = f"http://testserver/app/entry/{self.private_entry.id}/"
        Like.objects.create(
            author=f"http://testserver/authors/{self.author_b.id}",
            object=entry_url
        )

        # Log in as C (stranger)
        author_c = Author.objects.create(username="strangerC")
        session = self.client.session
        session['author_id'] = author_c.id
        session.save()

        # Let author C views B's 'Liked' history
        url = reverse('api:ApiAuthorLiked', kwargs={'author_id': self.author_a.id})
        response = self.client.get(url)
        
        # Check if the status code is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Author C cannot views B's 'Liked' on the private entry to C
        # Check if the list is empty
        self.assertEqual(len(response.data['src']), 0)

"""
Tests that there is only a single database for front and backend
"""
class DatabaseTest(TestCase):
    """
    User Story #77
    """
    def test_single_database(self):
        # Creates an author request in the front end
        client = Client()
        response = client.post("/app/process-signup/", data={"username": "FRIEND","password": "Password5"})
        # Checks if the author is in the database
        self.assertEqual(AuthorRequest.objects.count(), 1)
        # Manually adds an author to the database to avoid having to accept the author request
        author1 = Author(id = 1,username = "John",name = "John Doe",description = "This is John Doe's Account",host = "http://localhost:8000/api/",web = "http://localhost:8000/user/1",github = "https://github.com/John")
        author1.save()
        # Checks if the author is in the front end
        response = client.get("/app/user/1/")
        self.assertEqual(response.status_code,200)
        # Checks that the author appears on the frontend
        self.assertContains(response,"John")
        self.assertContains(response,"https://github.com/John")
        # Gets the author from the api
        authorURL = reverse("api:ApiAuthor",kwargs = {"id": 1})
        get1 = self.client.get(authorURL,format = "json")
        # Check that the details match
        self.assertEqual(get1.data["displayName"],author1.name)
        self.assertEqual(get1.data["github"],author1.github)
        self.assertEqual(get1.data["web"],author1.web)

class PublicEntriesAPITest(TestCase):
    def setUp(self):
        # Create some authors
        self.author1 = Author.objects.create(
            id=1, username="author1", name="Author One", host="http://testserver/", github="", web="", picture_url=""
        )
        self.author2 = Author.objects.create(
            id=2, username="author2", name="Author Two", host="http://testserver/", github="", web="", picture_url=""
        )

        # Create public entries
        for i in range(8):
            Entry.objects.create(
                id=uuid.uuid4(),
                author=self.author1 if i % 2 == 0 else self.author2,
                title=f"Public Entry {i+1}",
                description=f"Description {i+1}",
                content=f"Content {i+1}",
                contentType="text/plain",
                visibility="PUBLIC"
            )

        self.client = Client()

    def test_browse_public_entries(self):
        url = reverse('api:browse_public_entries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("page_number", data)
        self.assertIn("size", data)
        self.assertIn("count", data)
        self.assertIn("src", data)
        # There should be 8 public entries total
        self.assertEqual(data["count"], 8)
        # Default size is 5
        self.assertEqual(len(data["src"]), 5)

    def test_pagination(self):
        url = reverse('api:browse_public_entries') + "?page=2&size=5"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["page_number"], 2)
        self.assertEqual(data["size"], 5)
        # Second page should have remaining 3 entries
        self.assertEqual(len(data["src"]), 3)