from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Author, Entry, Like

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
        self.assertEqual(author.name,"Author3")
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
        self.assertEqual(author1.name,"Dalton")
        self.assertEqual(author2.name,"Low")

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

"""
Creates a test for the author and entry likes endpoint
"""
class AuthorEntryLikeEndpointTest(APITestCase):
    def test_author_entry_get_likes(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be like
        entry1 = Entry(title = "A",author = author1)
        entry1.save()
        like1 = Like(entry = entry1,user = author2)
        like1.save()
        # Gets the info from the website
        like_url = reverse("ApiAuthorAndEntryLikes",kwargs = {"author_id":author1.id,"entry_id":entry1.id})
        get1 = self.client.get(like_url,format="json")
        # Ensures there is exactly one like
        self.assertEqual(get1.data["count"],1)
        like = get1.data["src"][0]
        # Ensure the like has the correct entry
        self.assertEqual(like["object"].split("/")[-1],str(entry1.id))
        author = like["author"]
        self.assertEqual(author["displayName"],author2.name)

"""
Creates a test for the entry ikes endpoint
"""
class EntryLikeEndpointTest(APITestCase):
    def test_entry_get_likes(self):
        # Creates two users, one to make the entry and one to like it
        author1 = Author(username = "a",password = "b",name = "c",description = "d",host = "/api/",web = "/app/authors/1")
        author1.save()
        author2 = Author(username = "e",password = "f",name = "g",description = "h",host = "/api/",web = "/app/authors/2")
        author2.save()
        # Creates the entry that will be like
        entry1 = Entry(title = "A",author = author1)
        entry1.save()
        like1 = Like(entry = entry1,user = author2)
        like1.save()
        # Gets the info from the website
        like_url = reverse("ApiEntryLikes",kwargs = {"entry_id":entry1.id})
        get1 = self.client.get(like_url,format="json")
        # Ensures there is exactly one like
        self.assertEqual(get1.data["count"],1)
        like = get1.data["src"][0]
        # Ensure the like has the correct entry
        self.assertEqual(like["object"].split("/")[-1],str(entry1.id))
        author = like["author"]
        self.assertEqual(author["displayName"],author2.name)
        