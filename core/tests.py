from django.test import TestCase, Client
from .models import Author
import json

class AuthorApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        # create an author
        self.author = Author.objects.create(username="alice", name="Alice", github="http://github.com/alice")
        self.author.set_password("secret")
        self.author.save()

    def test_update_author_profile_via_api(self):
        # simulate login by setting session
        session = self.client.session
        session['author_id'] = self.author.id
        session['username'] = self.author.username
        session.save()

        url = f"/app/api/authors/{self.author.id}/"   # adjust path if you mounted differently
        payload = {
            "name": "Alice Newname",
            "description": "New bio",
            "github": "https://github.com/alice-updated"
        }

        response = self.client.put(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["author"]["name"], "Alice Newname")
        self.assertEqual(data["author"]["description"], "New bio")
        self.assertEqual(data["author"]["github"], "https://github.com/alice-updated")

        # verify DB persisted
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "Alice Newname")
        self.assertEqual(self.author.description, "New bio")
        self.assertEqual(self.author.github, "https://github.com/alice-updated")

    def test_cant_edit_other_author(self):
        # create second author
        other = Author.objects.create(username="bob")
        other.set_password("pw")
        other.save()

        # login as alice
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()

        url = f"/app/api/authors/{other.id}/"
        payload = {"name": "Hacker"}
        response = self.client.put(url, json.dumps(payload), content_type="application/json")
        self.assertIn(response.status_code, (401, 403))  # should be forbidden or unauthenticated
