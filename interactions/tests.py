from django.test import TestCase
from django.urls import reverse
from core.models import Author
from entries.models import Entry
from .models import Like, Comment
import uuid


class InteractionTests(TestCase):
    def setUp(self):
        self.user = Author.objects.create(username="user", password="x")
        self.other = Author.objects.create(username="other", password="x")
        self.entry = Entry.objects.create(
            title="foo",
            description="bar",
            contentType="text/plain",
            content="baz",
            author=self.other,
            visibility="PUBLIC",
        )
        # prepare URLs
        self.like_url = reverse("interactions:add_like", args=[self.entry.id])
        self.comment_url = reverse("interactions:add_comment", args=[self.entry.id])

    def login(self, author):
        session = self.client.session
        session["author_id"] = author.id
        session.save()

    def test_like_requires_login(self):
        response = self.client.post(self.like_url)
        self.assertRedirects(response, "/app/login/", fetch_redirect_response=False)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_toggle(self):
        self.login(self.user)
        # first click creates
        resp1 = self.client.post(self.like_url, follow=True)
        self.assertEqual(Like.objects.count(), 1)
        # second click removes
        resp2 = self.client.post(self.like_url, follow=True)
        self.assertEqual(Like.objects.count(), 0)

    def test_comment_requires_login(self):
        resp = self.client.post(self.comment_url, {"comment": "hi"})
        self.assertRedirects(resp, "/app/login/", fetch_redirect_response=False)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_creation(self):
        self.login(self.user)
        self.client.post(self.comment_url, {"comment": "nice"})
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertIn("/authors/", comment.author)
        self.assertEqual(comment.comment, "nice")
