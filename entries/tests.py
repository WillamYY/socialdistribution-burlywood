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
        
        # Create test authors
        self.author_a = self.AuthorModel.objects.create(
            username="web_user",
            name="Web User"
        )
        self.author_b = self.AuthorModel.objects.create(
            username="B",
            name="BB"
        )
        
        # Create entries with different visibilities
        self.public_entry = Entry.objects.create(
            author=self.author_a,
            title="Visible Post",
            content="Hello World",
            visibility="PUBLIC"
        )
        self.unlisted_entry = Entry.objects.create(
            author=self.author_a,
            title="Visible Post",
            content="Hello World",
            visibility="UNLISTED"
        )
        self.private_entry = Entry.objects.create(
            author=self.author_a,
            visibility="FRIENDS"
        )
        self.deleted_entry = Entry.objects.create(
            author=self.author_a,
            title="Invisible Post",
            content="Should not be seen ~",
            visibility="DELETED"
        )
        # Create a valid, tiny 1x1 pixel PNG in base64 format
        self.tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Save it to the database
        self.private_image_entry = Entry.objects.create(
            author=self.author_a,
            title="Test Image Entry with PNG",
            contentType="image/png;base64",
            content=f"data:image/png;base64,{self.tiny_png_b64}",
            visibility="FRIENDS"
        )
    
    def test_markdown_renders_in_html(self):
        """
        User Story #15: As an author, entries I make can be in CommonMark.
        """
        raw_content = "**Bold**"
        rendered_content = render_safe_markdown(raw_content)

        # entry.content stores the rendered HTML for text posts or base64 data for images.
        md_entry = Entry.objects.create(
            author=self.author_a,
            title="MD Test",
            contentType="text/markdown",
            content=rendered_content,
            visibility="PUBLIC"
        )
        
        url = reverse('get_entry', kwargs={'entry_id': md_entry.id})
        
        session = self.client.session
        session['author_id'] = self.author_a.id
        session.save()

        # Check if the markdown is rendered correctly in the HTML response
        response = self.client.get(url)
        self.assertContains(response, "<strong>Bold</strong>")

    def test_plain_text_entry(self):
        """
        User Story #14: As an author, entries I make can be in simple plain text.
        """
        session = self.client.session
        session['author_id'] = self.author_a.id
        session.save()

        url = reverse('api:ApiEntries', kwargs={'author_id': self.author_a.id})
        data = {
            "title": "Plain Text Test",
            "contentType": "text/plain",
            "content": "## Not a Header",
            "visibility": "PUBLIC",
        }

        response = self.client.post(url, data)
        self.assertIn(response.status_code, [200, 201])

        entry = Entry.objects.get(title="Plain Text Test")
        self.assertEqual(entry.contentType, "text/plain")
        self.assertEqual(entry.content, "## Not a Header")
        self.assertNotIn("<h2>", entry.content)
    
    def test_security_author_isolation(self):
        """
        User Story #22: Prove other authors cannot modify my entries.
        """
        # Point to the original author's entry
        url = reverse('api:ApiEntry', kwargs={
            'author_id': self.author_a.id, 
            'entry_id': self.public_entry.id
        })
        
        # Simulates being logged in as the Hacker
        session = self.client.session
        session['author_id'] = self.author_b.id
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
        self.public_entry.refresh_from_db()
        self.assertNotEqual(self.public_entry.title, "Hacked Title")
    
    def test_browser_manage_entries_flow(self):
        """
        User Story #21: As an author, I want to be able to use my web-browser to manage/author my entries.
        ChatGPT, OpenAI, 2026-03-15, https://chatgpt.com/share/69b78062-384c-8011-b02b-fa8e5afeb9ab
        """
        session = self.client.session
        session["author_id"] = self.author_a.id
        session.save()

        # Create through browser view
        create_url = reverse("create_entry")
        create_data = {
            "title": "Browser Created",
            "description": "created in web UI",
            "contentType": "text/plain",
            "content": "hello from browser",
            "visibility": "PUBLIC",
        }
        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Entry.objects.filter(title="Browser Created", author=self.author_a).exists())

        entry = Entry.objects.get(title="Browser Created", author=self.author_a)
        self.assertEqual(entry.content, "hello from browser")

        # Edit through browser view
        edit_url = reverse("edit_entry", kwargs={"entry_id": entry.id})
        edit_data = {
            "title": "Browser Edited",
            "description": "edited in web UI",
            "contentType": "text/plain",
            "content": "updated from browser",
            "visibility": "UNLISTED",
        }
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.title, "Browser Edited")
        self.assertEqual(entry.content, "updated from browser")
        self.assertEqual(entry.visibility, "UNLISTED")

        # Delete through browser view
        delete_url = reverse("delete_entry", kwargs={"entry_id": entry.id})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.visibility, "DELETED")

    def test_markdown_entry_can_link_to_images(self):
        """
        User Story #18: As an author, entries I create that are in CommonMark can link to images.
        ChatGPT, OpenAI, 2026-03-15, https://chatgpt.com/share/69b78062-384c-8011-b02b-fa8e5afeb9ab
        """
        raw_markdown = 'Here is an image ![tiny](/media/hosted_images/test.png)'
        rendered = render_safe_markdown(raw_markdown)

        entry = Entry.objects.create(
            author=self.author_a,
            title="Markdown Image Link",
            description="markdown image",
            contentType="text/markdown",
            content=rendered,
            content_raw=raw_markdown,
            visibility="PUBLIC",
        )

        session = self.client.session
        session["author_id"] = self.author_a.id
        session.save()

        url = reverse("get_entry", kwargs={"entry_id": entry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<img")
        self.assertContains(response, 'src="/media/hosted_images/test.png"', html=False)
        self.assertContains(response, 'alt="tiny"', html=False)
        
    def test_get_entry_public_deleted_access(self):
        """
        User Story #91: As an author, entries I create should always be visible to me until they are deleted.
        """
        public_url = reverse('get_entry', kwargs={'entry_id': self.public_entry.id})
        unlisted_url = reverse('get_entry', kwargs={'entry_id': self.unlisted_entry.id})
        deleted_url = reverse('get_entry', kwargs={'entry_id': self.deleted_entry.id})
        
        # Log in as author A
        session = self.client.session
        session['author_id'] = self.author_a.id
        session.save()

        # Check if the status code is 200 OK
        self.assertEqual(self.client.get(public_url).status_code, 200)
        self.assertEqual(self.client.get(unlisted_url).status_code, 200)
        self.assertEqual(self.client.get(deleted_url).status_code, 404)

    def test_get_entry_friends_only(self):
        """
        User Story #41: As an author, I don't anyone who isn't a friend to be able to see my friends-only entries and images.
        """
        # Note: the image endpoint is separate from the web UI
        private_img_url = reverse('api:ApiEntryImage', kwargs={'author_id': self.author_a.id, 'entry_id': self.private_image_entry.id})
        private_text_url = reverse('get_entry', kwargs={'entry_id': self.private_entry.id})

        # Log in as B (stranger)
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        # Check if B cannot access A's friends-only entry
        response_text = self.client.get(private_text_url)
        response_img = self.client.get(private_img_url)
        self.assertEqual(response_img.status_code, 403)
        self.assertEqual(response_text.status_code, 200)
        self.assertFalse(response_text.context['allowed'])

        # Make B a friend of A (Mutual Follow)
        self.author_a.followers.add(self.author_b)
        self.author_b.followers.add(self.author_a)

        # Check if B can now access
        response_text = self.client.get(private_text_url)
        response_img = self.client.get(private_img_url)
        self.assertEqual(response_img.status_code, 200)
        self.assertEqual(response_text.status_code, 200)
        self.assertTrue(response_text.context['allowed'])

    def test_see_deleted_entries(self):
        """
        User Story #42: As an author, I don't want anyone except the node admin to see my deleted entries.
        """
        deleted_url = reverse('get_entry', kwargs={'entry_id': self.deleted_entry.id})
        
        # Log in as author A
        session = self.client.session
        session['author_id'] = self.author_a.id
        session.save()

        # Check if the status code is 404, not found since deleted
        self.assertEqual(self.client.get(deleted_url).status_code, 404)

        # Node admin able to see the deleted entry
        self.assertTrue(Entry.objects.filter(id=self.deleted_entry.id).exists())

    def test_see_public_unlisted(self):
        """
        User Story #40: As an author, I want everyone to be able to see my public and unlisted entries, if they have a link to it.
        """
        public_url = reverse('get_entry', kwargs={'entry_id': self.public_entry.id})
        unlisted_url = reverse('get_entry', kwargs={'entry_id': self.unlisted_entry.id})

        # Not logged in, a generic user
        session = self.client.session
        session['author_id'] = None
        session.save()

        # Check if generic user can access user A's public and unlisted entries
        public_response = self.client.get(public_url)
        unlisted_response = self.client.get(unlisted_url)
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(unlisted_response.status_code, 200)

    def test_see_friends_only(self):
        """
        User story #36: As an author, I want to be able to make my entries "friends-only," so that I don't have to worry about people I don't know seeing them.
        """
        private_url = reverse('get_entry', kwargs={'entry_id': self.private_entry.id})
        
        # Log in as B (stranger)
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        friend_response = self.client.get(private_url)
        self.assertContains(friend_response, "<h1>Entry Unavailable</h1>")

    def test_everyone_see_public_entries(self):
        """
        User story #34: As an author, I want to be able to make my entries "public", so that everyone can see them.
        """
        entries_url = reverse("view_entries", kwargs={"author_id": self.author_a.id})

        # Not logged in, a generic user
        session = self.client.session
        session['author_id'] = None
        session.save()

        response = self.client.get(entries_url)
        self.assertContains(response, "<h2 class=\"entry-title\">Visible Post</h2>")
        self.assertContains(response, "<span class=\"badge-visibility\">PUBLIC</span>")

    def test_followers_see_unlisted_entries(self):
        """
        User story #35: As an author, I want to be able to make my entries "unlisted," so that my followers see them, and anyone with the link can also see them.
        """
        unlisted_url = reverse('get_entry', kwargs={'entry_id': self.unlisted_entry.id})
        
        # Not logged in, a generic user
        session = self.client.session
        session['author_id'] = None
        session.save()

        # anyone with the link can see the unlisted post
        unlisted_response = self.client.get(unlisted_url)
        self.assertEqual(unlisted_response.status_code, 200)

        # Logged in as B, follower of A
        session = self.client.session
        session['author_id'] = self.author_b.id
        session.save()

        # makes B follow A
        self.author_a.followers.add(self.author_b)

        entries_url = reverse("view_entries", kwargs={"author_id": self.author_a.id})

        response = self.client.get(entries_url)
        self.assertContains(response, "<h2 class=\"entry-title\">Visible Post</h2>")
        self.assertContains(response, "<span class=\"badge-visibility\">UNLISTED</span>")

    def test_get_entry_url(self):
        """
        User Story #41: As a reader, I can get a link to a public or unlisted entry, so I can send it to my friends over email, discord, slack, etc.
        """
        public_url = reverse('get_entry', kwargs={'entry_id': self.public_entry.id})
        unlisted_url = reverse('get_entry', kwargs={'entry_id': self.unlisted_entry.id})
        private_url = reverse('get_entry', kwargs={'entry_id': self.private_entry.id})
        deleted_url = reverse('get_entry', kwargs={'entry_id': self.deleted_entry.id})

        # Not logged in, a generic reader
        session = self.client.session
        session['author_id'] = None
        session.save()

        # Reader should only be able to access the public and unlisted entries given the URL
        public_url_response = self.client.get(public_url)
        self.assertTrue(public_url_response.context['allowed'])
        unlisted_url_response = self.client.get(unlisted_url)
        self.assertTrue(unlisted_url_response.context['allowed'])

        private_url_response = self.client.get(private_url)
        self.assertFalse(private_url_response.context['allowed'])
        deleted_url_response = self.client.get(deleted_url)
        self.assertEqual(deleted_url_response.status_code, 404)