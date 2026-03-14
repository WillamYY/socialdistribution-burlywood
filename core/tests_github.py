"""
Tests for GitHub activity sync (User Story #5).
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase

from core.models import Author
from core.services import (
    extract_github_username,
    format_github_event_as_entry,
    sync_author_github_activity,
)
from entries.models import Entry


class ExtractGitHubUsernameTest(TestCase):
    def test_extract_standard_url(self):
        self.assertEqual(extract_github_username('https://github.com/octocat'), 'octocat')
        self.assertEqual(extract_github_username('http://github.com/octocat'), 'octocat')

    def test_extract_url_with_trailing_slash(self):
        self.assertEqual(extract_github_username('https://github.com/octocat/'), 'octocat')

    def test_extract_empty_or_none(self):
        self.assertIsNone(extract_github_username(''))
        self.assertIsNone(extract_github_username(None))

    def test_extract_invalid_url(self):
        self.assertIsNone(extract_github_username('https://gitlab.com/user'))


class FormatGitHubEventTest(TestCase):
    def test_push_event(self):
        event = {
            'id': 123,
            'type': 'PushEvent',
            'repo': {'name': 'owner/repo'},
            'payload': {
                'ref': 'refs/heads/main',
                'size': 3,
                'commits': [
                    {'sha': 'abc1234', 'message': 'Fix bug'},
                    {'sha': 'def5678', 'message': 'Add feature'},
                ],
            },
            'created_at': '2026-03-13T12:00:00Z',
        }
        result = format_github_event_as_entry(event)
        self.assertIsNotNone(result)
        self.assertIn('Pushed', result['title'])
        self.assertIn('owner/repo', result['title'])
        self.assertEqual(result['description'], 'Push to main')
        self.assertIn('Fix bug', result['content_raw'])

    def test_fork_event(self):
        event = {
            'id': 456,
            'type': 'ForkEvent',
            'repo': {'name': 'owner/repo'},
            'payload': {
                'forkee': {'full_name': 'me/forked-repo'},
            },
            'created_at': '2026-03-13T12:00:00Z',
        }
        result = format_github_event_as_entry(event)
        self.assertIsNotNone(result)
        self.assertIn('Forked', result['title'])
        self.assertIn('owner/repo', result['title'])

    def test_watch_event(self):
        event = {
            'id': 789,
            'type': 'WatchEvent',
            'repo': {'name': 'owner/starred-repo'},
            'payload': {'action': 'started'},
            'created_at': '2026-03-13T12:00:00Z',
        }
        result = format_github_event_as_entry(event)
        self.assertIsNotNone(result)
        self.assertIn('Starred', result['title'])

    def test_unsupported_event_returns_none(self):
        event = {
            'id': 999,
            'type': 'SomeUnknownEvent',
            'repo': {'name': 'owner/repo'},
            'created_at': '2026-03-13T12:00:00Z',
        }
        result = format_github_event_as_entry(event)
        self.assertIsNone(result)


class SyncAuthorGitHubTest(TestCase):
    def setUp(self):
        self.author = Author.objects.create(
            id=1,
            username='testuser',
            name='Test User',
            password='hashed',
            host='http://testserver/api/',
            web='http://testserver/app/authors/1',
            github='https://github.com/octocat',
        )

    @patch('core.services.fetch_github_events')
    def test_sync_creates_entries(self, mock_fetch):
        mock_fetch.return_value = [
            {
                'id': 111222333,
                'type': 'PushEvent',
                'repo': {'name': 'octocat/repo'},
                'payload': {'ref': 'refs/heads/main', 'size': 1, 'commits': []},
                'created_at': '2026-03-13T12:00:00Z',
            },
        ]
        created, err = sync_author_github_activity(self.author)
        self.assertIsNone(err)
        self.assertEqual(created, 1)
        entry = Entry.objects.get(github_event_id=111222333)
        self.assertEqual(entry.author, self.author)
        self.assertEqual(entry.visibility, 'PUBLIC')
        self.assertIn('Pushed', entry.title)

    @patch('core.services.fetch_github_events')
    def test_sync_no_duplicates(self, mock_fetch):
        mock_fetch.return_value = [
            {
                'id': 444555666,
                'type': 'PushEvent',
                'repo': {'name': 'octocat/repo'},
                'payload': {'ref': 'refs/heads/main', 'size': 1, 'commits': []},
                'created_at': '2026-03-13T12:00:00Z',
            },
        ]
        created1, _ = sync_author_github_activity(self.author)
        created2, _ = sync_author_github_activity(self.author)
        self.assertEqual(created1, 1)
        self.assertEqual(created2, 0)
        self.assertEqual(Entry.objects.filter(github_event_id=444555666).count(), 1)

    def test_sync_no_github_url(self):
        self.author.github = ''
        self.author.save()
        created, err = sync_author_github_activity(self.author)
        self.assertEqual(created, 0)
        self.assertIn('No valid GitHub', err)

    @patch('core.services.fetch_github_events')
    def test_sync_api_failure(self, mock_fetch):
        mock_fetch.return_value = None
        created, err = sync_author_github_activity(self.author)
        self.assertEqual(created, 0)
        self.assertIn('Failed to fetch', err)
