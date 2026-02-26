from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Author

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