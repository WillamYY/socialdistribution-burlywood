from django.test import TestCase, Client
from django.urls import reverse
from core.models import Author, FollowRequest
from django.core.files.uploadedfile import SimpleUploadedFile

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