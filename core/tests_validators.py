"""
Tests for core validators (username, password, GitHub URL).
"""
from django.test import TestCase
from core.validators import validate_username, validate_password, validate_github_url


class ValidateUsernameTestCase(TestCase):
    def test_valid_usernames(self):
        for u in ("alice", "bob123", "user_name", "user-name", "a1b2c3"):
            ok, err = validate_username(u)
            self.assertTrue(ok, f"'{u}' should be valid")
            self.assertIsNone(err)

    def test_too_short(self):
        ok, err = validate_username("ab")
        self.assertFalse(ok)
        self.assertIn("3", err)

    def test_too_long(self):
        ok, err = validate_username("a" * 41)
        self.assertFalse(ok)
        self.assertIn("40", err)

    def test_invalid_characters(self):
        for u in ("user name", "user@host", "user.name", "user!name", "日本語"):
            ok, err = validate_username(u)
            self.assertFalse(ok, f"'{u}' should be invalid")
            self.assertIsNotNone(err)


class ValidatePasswordTestCase(TestCase):
    def test_valid_passwords(self):
        for p in ("Secret123", "mypass99", "a1b2c3d4", "ValidPass1"):
            ok, err = validate_password(p)
            self.assertTrue(ok, f"Password should be valid")
            self.assertIsNone(err)

    def test_too_short(self):
        ok, err = validate_password("Ab1")
        self.assertFalse(ok)
        self.assertIn("8", err)

    def test_disallowed_passwords(self):
        for p in ("password123", "12345678", "Password1", "qwerty123"):
            ok, err = validate_password(p)
            self.assertFalse(ok, f"'{p}' should be disallowed")
            self.assertIn("common", err.lower())

    def test_no_letter(self):
        ok, err = validate_password("9999888877")  # numbers only, not in disallowed list
        self.assertFalse(ok)
        self.assertIn("letter", err)

    def test_no_number(self):
        ok, err = validate_password("abcdefgh")
        self.assertFalse(ok)
        self.assertIn("number", err)


class ValidateGithubUrlTestCase(TestCase):
    def test_valid_urls(self):
        for url in (
            "https://github.com/octocat",
            "https://github.com/octocat/",
            "http://github.com/user",
            "https://www.github.com/user",
        ):
            ok, err = validate_github_url(url)
            self.assertTrue(ok, f"'{url}' should be valid")
            self.assertIsNone(err)

    def test_empty_ok(self):
        ok, err = validate_github_url("")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_invalid_urls(self):
        for url in (
            "https://gitlab.com/user",
            "https://github.com",  # no username
            "not-a-url",
            "https://github.com/user/repo",  # repo path
        ):
            ok, err = validate_github_url(url)
            self.assertFalse(ok, f"'{url}' should be invalid")
            self.assertIn("GitHub", err)
