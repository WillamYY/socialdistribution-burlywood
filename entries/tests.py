from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import Author
from entries.models import Entry
from entries.views import render_safe_markdown


class StreamApiTests(TestCase):
    def setUp(self):
        self.viewer = Author.objects.create(username="viewer", password="x")
        self.followed = Author.objects.create(username="followed", password="x")
        self.friend = Author.objects.create(username="friend", password="x")
        self.outsider = Author.objects.create(username="outsider", password="x")

        # viewer follows followed
        self.followed.followers.add(self.viewer)

        # viewer and friend are mutual followers
        self.friend.followers.add(self.viewer)
        self.viewer.followers.add(self.friend)

        now = timezone.now()

        self.entry_public_outsider = Entry.objects.create(
            title="Public outsider",
            description="desc",
            contentType="text/plain",
            content="old content",
            author=self.outsider,
            visibility="PUBLIC",
        )
        self.entry_unlisted_followed = Entry.objects.create(
            title="Unlisted followed",
            description="desc",
            contentType="text/plain",
            content="unlisted followed",
            author=self.followed,
            visibility="UNLISTED",
        )
        self.entry_friends_friend = Entry.objects.create(
            title="Friends friend",
            description="desc",
            contentType="text/plain",
            content="friends only",
            author=self.friend,
            visibility="FRIENDS",
        )
        self.entry_unlisted_outsider = Entry.objects.create(
            title="Unlisted outsider",
            description="desc",
            contentType="text/plain",
            content="unlisted outsider",
            author=self.outsider,
            visibility="UNLISTED",
        )
        self.entry_public_viewer = Entry.objects.create(
            title="Public viewer",
            description="desc",
            contentType="text/plain",
            content="viewer public",
            author=self.viewer,
            visibility="PUBLIC",
        )
        self.entry_deleted = Entry.objects.create(
            title="Deleted entry",
            description="desc",
            contentType="text/plain",
            content="deleted",
            author=self.viewer,
            visibility="PUBLIC",
        )

        # Adjust timestamps for deterministic ordering
        Entry.objects.filter(id=self.entry_public_outsider.id).update(published=now - timedelta(days=2))
        Entry.objects.filter(id=self.entry_unlisted_followed.id).update(published=now - timedelta(days=1))
        Entry.objects.filter(id=self.entry_friends_friend.id).update(published=now)

        # Edit an entry to ensure latest content is returned
        self.entry_public_outsider.content = "updated content"
        self.entry_public_outsider.save()

        # Delete an entry for deletion test
        self.entry_deleted.delete()

        self.stream_url = reverse("stream_api", args=[self.viewer.id])

    def login_as(self, author):
        session = self.client.session
        session["author_id"] = author.id
        session["username"] = author.username
        session.save()

    def test_stream_requires_auth(self):
        response = self.client.get(self.stream_url)
        self.assertEqual(response.status_code, 401)

    def test_stream_filters_and_orders(self):
        self.login_as(self.viewer)
        response = self.client.get(self.stream_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        entries = data["src"]
        ids = [item["id"] for item in entries]

        # Included: all PUBLIC
        self.assertIn(str(self.entry_public_outsider.id), ids)
        self.assertIn(str(self.entry_public_viewer.id), ids)

        # Included: UNLISTED from followed
        self.assertIn(str(self.entry_unlisted_followed.id), ids)

        # Included: FRIENDS from mutual friends
        self.assertIn(str(self.entry_friends_friend.id), ids)

        # Excluded: UNLISTED from non-followed
        self.assertNotIn(str(self.entry_unlisted_outsider.id), ids)

        # Excluded: deleted entry
        self.assertNotIn(str(self.entry_deleted.id), ids)

        # Sorted newest first by published
        published_times = [datetime.fromisoformat(e["published"]) for e in entries]
        self.assertEqual(published_times, sorted(published_times, reverse=True))

        # Latest version (edited content)
        edited_entry = next(e for e in entries if e["id"] == str(self.entry_public_outsider.id))
        self.assertEqual(edited_entry["content"], "updated content")

class EntryWebUITests(TestCase):
    """
    Creates a series of tests for the web
    """
    def setUp(self):
        self.AuthorModel = Entry._meta.get_field('author').related_model
        self.client = Client()
        
        # Create a test author
        self.author = self.AuthorModel.objects.create(
            username="web_user",
            name="Web User"
        )
        
        # Create a public entry and a deleted entry
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="Visible Post",
            content="Hello World",
            visibility="PUBLIC"
        )
        self.deleted_entry = Entry.objects.create(
            author=self.author,
            title="Invisible Post",
            content="Should not be seen ~",
            visibility="DELETED"
        )

    def test_my_entries_loads_for_author(self):
        """
        Verify the page loads correctly when the author_id is in the session.
        """
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()
        
        url = reverse('view_my_entries')
        response = self.client.get(url)

        # Check if it handles the request successfully
        self.assertEqual(response.status_code, 200)

        # Check if it handles the proper visibility
        self.assertContains(response, "Visible Post")
        self.assertNotContains(response, "Invisible Post")

    def test_markdown_renders_in_html(self):
        """
        User Story #15: As an author, entries I make can be in CommonMark.
        """
        raw_content = "**Bold**"
        rendered_content = render_safe_markdown(raw_content)

        # entry.content stores the rendered HTML for text posts or base64 data for images.
        md_entry = Entry.objects.create(
            author=self.author,
            title="MD Test",
            contentType="text/markdown",
            content=rendered_content,
            visibility="PUBLIC"
        )
        
        url = reverse('get_entry', kwargs={'entry_id': md_entry.id})
        
        session = self.client.session
        session['author_id'] = self.author.id
        session.save()

        # Check if the markdown is rendered correctly in the HTML response
        response = self.client.get(url)
        self.assertContains(response, "<strong>Bold</strong>")