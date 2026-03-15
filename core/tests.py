from django.test import TestCase, Client
from django.urls import reverse
from core.models import Author, FollowRequest
from interactions.models import Like, Comment
from entries.models import Entry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.postgres.fields import ArrayField
import uuid

class UnfollowAPITestCase(TestCase):
    """
    Tests for Author model and related API endpoints.
    """
    def setUp(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')

        # author1 follows author2
        self.author2.followers.add(self.author1)

        self.client = Client()
        self.url = reverse('api-unfollow-author', args=[self.author1.id, self.author2.id])

    def test_unfollow_success(self):
        """
        Test that an author can send a follow request to another author.
        """
        response = self.client.delete(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.author2.followers.filter(id=self.author1.id).exists())

    def test_unfollow_not_following(self):
        """
        Test that trying to unfollow an author you aren't following returns 404.
        """
        self.author2.followers.remove(self.author1)
        response = self.client.delete(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Not following', response.json()['detail'])

    def test_unfollow_forbidden(self):
        """
        Test that an author cannot unfollow another using invalid auth_id.
        """
        response = self.client.delete(f'{self.url}?auth_id={self.author2.id}')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Forbidden', response.json()['detail'])

class FriendsAPITestCase(TestCase):
    """
    Tests the friends list API endpoint (mutual following).
    """
    def setUp(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')
        # Mutual following
        self.author1.following.add(self.author2)
        self.author2.following.add(self.author1)
        self.client = Client()
        self.url = reverse('api-list-friends', args=[self.author1.id])

    def test_friends_list(self):
        """
        Test that friends endpoint returns only mutual followers.
        """
        response = self.client.get(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"friends":[{"id": self.author2.id,"username":"author2"}]})

class FollowRequestsAPITestCase(TestCase):
    """
    Tests listing pending follow requests for an author.
    """
    def setUp(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')
        # Author2 requests to follow Author1
        FollowRequest.objects.create(requester=self.author2, target=self.author1)
        self.client = Client()
        self.url = reverse('api-list-follow-requests', args=[self.author1.id])

    def test_follow_requests_list(self):
        """
        Test that pending follow requests are returned correctly.
        """
        response = self.client.get(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['follow_requests']), 1)
        self.assertEqual(response.json()['follow_requests'][0]['requester_username'], 'author2') 

class FollowRequestsApprovalTestCase(TestCase):
    """
    Tests approving and denying follow requests.
    """
    def setUp(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')
        self.follow_req = FollowRequest.objects.create(requester=self.author2, target=self.author1)
        self.client = Client()

    def test_approve_follow(self):
        url = reverse('api-approve-follow', args=[self.follow_req.id])
        response = self.client.post(f'{url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.author2 in self.author1.followers.all())
        self.assertFalse(FollowRequest.objects.filter(id=self.follow_req.id).exists())

    def test_deny_follow(self):
        """
        Test denying a follow request removes it without adding to followers.
        """
        url = reverse('api-deny-follow', args=[self.follow_req.id])
        response = self.client.post(f'{url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FollowRequest.objects.filter(id=self.follow_req.id).exists())
        self.assertFalse(self.author2 in self.author1.followers.all())   

class FollowAPITestCase(TestCase):
    """
    Tests the follow author API endpoint.
    """
    def setUp(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')

        self.client = Client()
        self.url = reverse('api-follow-author', args=[self.author2.id])

    def test_follow_success(self):
        response = self.client.post(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(FollowRequest.objects.filter(requester=self.author1, target=self.author2).exists())

    def test_follow_self(self):
        """
        Test that an author cannot follow themselves.
        """
        url_self = reverse('api-follow-author', args=[self.author1.id])
        response = self.client.post(f'{url_self}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot follow yourself', response.json()['detail'])

    def test_follow_already_sent(self):
        """
        Test that sending a duplicate follow request returns conflict.
        """
        FollowRequest.objects.create(requester=self.author1, target=self.author2)
        response = self.client.post(f'{self.url}?auth_id={self.author1.id}')
        self.assertEqual(response.status_code, 409)
        self.assertIn('Follow request already sent', response.json()['detail'])

class EditProfileAPITestCase(TestCase):
    """
    Tests the edit profile API endpoint.
    """
    def setUp(self):
        self.author = Author.objects.create(
            username='author1',
            password='pass1',
            description='Initial description'
        )
        self.client = Client()
        self.url = reverse('EditProfileView') 

        # Set session for logged-in user
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()

    def test_get_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.author.username, response.content.decode())

    def test_edit_profile_success(self):
        """
        Test updating name, description, and github fields.
        """
        data = {
            "name": "New Name",
            "description": "New description",
            "github": "https://github.com/new",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Profile updated successfully", response.content.decode())

        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "New Name")
        self.assertEqual(self.author.description, "New description")
        self.assertEqual(self.author.github, "https://github.com/new")

    def test_edit_profile_picture(self):
        img = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")
        response = self.client.post(
            self.url,
            {
                "picture": img,
                "name": "Test Name",
                "description": "Test Description",
                "github": "",
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.author.refresh_from_db()
        self.assertTrue(self.author.picture)

    def test_edit_profile_forbidden(self):
        """
        Test that editing profile fails when not logged-in.
        """
        session = self.client.session
        del session['author_id']
        session.save()

        response = self.client.post(self.url, {"name": "Fail"})
        self.assertEqual(response.status_code, 302)  # redirect to login
        self.assertIn("/login", response.url)

class FollowerFollowingFriendsTestCase(TestCase):
    """
    User story #55: As an author, my node will know about my followers, who I am following, and my friends, so that I don't have to keep track of it myself.
    """
    def test_follower_following_friend(self):
        self.author1 = Author.objects.create(username='author1', password='pass1')
        self.author2 = Author.objects.create(username='author2', password='pass2')

        # initially no one is following each other
        self.assertEqual(self.author1.followers.count(), 0)
        self.assertEqual(self.author2.followers.count(), 0)
        
        # author 2 follows author 1
        self.author1.followers.add(self.author2)
        self.assertEqual(self.author1.followers.count(), 1)
        self.assertEqual(self.author2.followers.count(), 0)

        # author 1 follows author 2
        self.author2.followers.add(self.author1)
        self.assertEqual(self.author1.followers.count(), 1)
        self.assertEqual(self.author1.followers.count(), 1)
        self.assertEqual(self.author1.friends().count(), 1)
        self.assertEqual(self.author2.friends().count(), 1)

class ProfileViewTestCase(TestCase):
    def test_get_profile_entries(self):
        """
        User story #6: As an author, I want my profile page to show my public entries (most recent first), so they can decide if they want to follow me.
        """
        # creates a generic author
        self.author = Author.objects.create(
            username='author1',
            password='pass1',
            description='Initial description'
        )
        self.client = Client()
        self.url = reverse('EditProfileView')

        # author creates entries of 4 types of visibility
        entry1 = Entry(title = "public entry" ,description = "public entry", contentType = "text/plain",content = "public entry",author = self.author, visibility = "PUBLIC")
        entry1.save()
        entry2 = Entry(title = "unlisted entry" ,description = "unlisted entry", contentType = "text/plain",content = "unlisted entry",author = self.author, visibility = "UNLISTED")
        entry2.save()
        entry3 = Entry(title = "friends entry" ,description = "friends entry", contentType = "text/plain",content = "friends entry",author = self.author, visibility = "FRIENDS")
        entry3.save()
        entry4 = Entry(title = "deleted entry" ,description = "deleted entry", contentType = "text/plain",content = "deleted entry",author = self.author, visibility = "DELETED")
        entry4.save()

        profile_url = reverse('ProfileDisplay', kwargs={'id': self.author.id})

        # Not logged in, a generic reader
        session = self.client.session
        session['author_id'] = None
        session.save()

        response = self.client.get(profile_url)
        self.assertContains(response, f"<h2 class=\"entry-title\">{entry1.title}</h2>")
        self.assertNotContains(response, f"<h2 class=\"entry-title\">{entry2.title}</h2>")
        self.assertNotContains(response, f"<h2 class=\"entry-title\">{entry3.title}</h2>")
        self.assertNotContains(response, f"<h2 class=\"entry-title\">{entry4.title}</h2>")

        # test database only gets the one entry
        self.assertEqual(Entry.objects.filter(author = self.author, visibility="PUBLIC").count(), 1)

"""
Creates the test for the admin user stories
"""
class AdminUserStoryTestCase(TestCase):
    """
    Tests using SQL queries on database
    User Story #75
    """
    def test_sql_queries(self):
        # Tries sql queries on the Authors
        author1 = Author(username = "John",name = "John Doe",description = "This is John Doe's Account",host = "http://localhost:8000/api/",web = "http://localhost:8000/user/1")
        author1.save()
        author2 = Author(username = "Jane",name = "Jane Doe",description = "This is Jane Doe's Account",host = "http://localhost:8000/api/",web = "http://localhost:8000/user/2")
        author2.save()
        self.assertEqual(list(Author.objects.raw("SELECT * FROM core_author")),[author1,author2])
        self.assertEqual(Author.objects.raw("SELECT description, id FROM core_author WHERE username = 'Jane'")[0].description,"This is Jane Doe's Account")

        # SQL queries on Follow Request
        followRequest1 = FollowRequest(requester = author1,target = author2)
        followRequest1.save()
        followRequest2 = FollowRequest(requester = author2,target = author1)
        followRequest2.save()
        self.assertEqual(list(FollowRequest.objects.raw("SELECT * FROM core_followrequest")),[followRequest1,followRequest2])
        self.assertEqual(FollowRequest.objects.raw(f"SELECT requester_id, id FROM core_followrequest WHERE target_id = 2")[0].requester_id,1)

        # SQL queries on Entries
        entry1 = Entry(title = "John's Post",description = "This is the first entry",contentType = "text/plain",content = "NUMBER 1!",author = author1, visibility = "PUBLIC")
        entry1.save()
        entry2 = Entry(title = "Jane's Post",description = "This is the second entry",contentType = "text/plain",content = "NUMBER 2!",author = author2, visibility = "PRIVATE")
        entry2.save()
        self.assertEqual(list(Entry.objects.raw("SELECT * FROM entries_entry")),[entry1, entry2])
        self.assertEqual(Entry.objects.raw("SELECT title, id FROM entries_entry WHERE content = 'NUMBER 2!'")[0].title,"Jane's Post")

        # SQL queries on Like
        firstUUID = uuid.uuid4()
        entry1Id = f"http://localhost:8000/api/authors/{entry1.author.id}/entries/{entry1.id}/"
        like1 = Like(author = author1.web,object = entry1Id, id = "http://localhost:8000/likes/" + str(firstUUID), uuid = firstUUID)
        like1.save()
        secondUUID = uuid.uuid4()
        entry2Id = f"http://localhost:8000/api/authors/{entry2.author.id}/entries/{entry2.id}/"
        like2 = Like(author = author2.web,object = entry2Id, id = "http://localhost:8000/likes/" + str(secondUUID), uuid = secondUUID)
        like2.save()
        self.assertEqual(list(Like.objects.raw("SELECT * from interactions_like")),[like1,like2])
        self.assertEqual(Like.objects.raw(f"SELECT * FROM interactions_like WHERE id = %s",["http://localhost:8000/likes/" + str(firstUUID)])[0].uuid, firstUUID)

        # SQL queries on comments (Reuses the uuid's from like)
        comment1Id = f"http://localhost:8000/api/comments/{firstUUID}"
        comment1 = Comment(author = author1.web,entry = entry1Id, id = comment1Id, comment = "HELLO",contentType = "text/plain")
        comment1.save()
        comment2Id = f"http://localhost:8000/api/comments/{secondUUID}"
        comment2 = Comment(author = author2.web,entry = entry2Id, id = comment2Id, comment = "GOODBYE",contentType = "text/plain")
        comment2.save()
        self.assertEqual(list(Comment.objects.raw("SELECT * from interactions_comment")),[comment1,comment2])
        self.assertEqual(Comment.objects.raw(f"SELECT * FROM interactions_comment WHERE author = %s",[author1.web])[0].comment, "HELLO")

    """
    Checks that arrays are not stored in database fields
    User Story #75
    """
    def test_array_database_field(self):
        # Ensures no authors have arrayfields
        for field in Author._meta.get_fields():
            self.assertFalse(isinstance(field,ArrayField))
        # Ensures no follow request have arrayfields
        for field in FollowRequest._meta.get_fields():
            self.assertFalse(isinstance(field,ArrayField))
        # Ensures no entires have arrayfields
        for field in Entry._meta.get_fields():
            self.assertFalse(isinstance(field,ArrayField))
        # Ensures no comments have arrayfields
        for field in Comment._meta.get_fields():
            self.assertFalse(isinstance(field,ArrayField))
        # Ensures no likes have arrayfields
        for field in Like._meta.get_fields():
            self.assertFalse(isinstance(field,ArrayField))