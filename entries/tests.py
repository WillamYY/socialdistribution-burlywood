import json
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
        # Create a valid, tiny 1x1 pixel PNG in base64 format
        self.tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Save it to the database
        self.image_entry = Entry.objects.create(
            author=self.author,
            title="Test Image Entry with PNG",
            contentType="image/png;base64",
            content=f"data:image/png;base64,{self.tiny_png_b64}",
            visibility="PUBLIC"
        )
    
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

    def test_plain_text_entry(self):
        """
        User Story #14: As an author, entries I make can be in simple plain text.
        """
        url = reverse('api:ApiEntries', kwargs={'author_id': self.author.id})
        data = {"contentType": "text/plain", "content": "## Not a Header"}
        self.client.post(url, data, format='json')
        
        entry = Entry.objects.get(content="## Not a Header")
        self.assertEqual(entry.contentType, "text/plain")
        # Check if it's not converted to <h2> in the DB
        self.assertNotIn("<h2>", entry.content)
    
    def test_security_author_isolation(self):
        """
        User Story #22: Prove other authors cannot modify my entries.
        """
        # Create a different author (the "Hacker")
        AuthorModel = Entry._meta.get_field('author').related_model
        other_author = AuthorModel.objects.create(username="hacker", name="Hacker")

        # Point to the original author's entry
        url = reverse('api:ApiEntry', kwargs={
            'author_id': self.author.id, 
            'entry_id': self.image_entry.id
        })
        
        # Simulates being logged in as the Hacker
        session = self.client.session
        session['author_id'] = other_author.id
        session.save()
        
        # Try to PUT (edit) the first author's entry
        update_data = {"title": "Hacked Title"}
        response = self.client.put(
                    url, 
                    data=json.dumps(update_data), 
                    content_type='application/json'
                )
                        
        # Should be 403 Forbidden
        self.assertEqual(response.status_code, 403)
        
        # Ensure the title didn't actually change
        self.image_entry.refresh_from_db()
        self.assertNotEqual(self.image_entry.title, "Hacked Title")