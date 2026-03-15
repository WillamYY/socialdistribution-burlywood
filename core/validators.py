"""
Validation helpers for username, password, and GitHub URL.
"""
import re

# Username: 3–40 chars, letters, numbers, underscores, hyphens only
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,40}$")

# GitHub profile URL: https://github.com/username
GITHUB_URL_PATTERN = re.compile(
    r"^https?://(www\.)?github\.com/[a-zA-Z0-9_-]+/?$",
    re.IGNORECASE,
)

# Weak / disallowed passwords (case-insensitive)
DISALLOWED_PASSWORDS = frozenset({
    "password", "password1", "password12", "password123", "password1234",
    "12345678", "123456789", "1234567890", "qwerty123", "abc12345",
    "letmein", "welcome", "admin", "administrator", "root", "test",
    "passw0rd", "password!", "Password1", "Password123",
})


def validate_username(username):
    """
    Validate username format.
    Returns (True, None) if valid, else (False, error_message).
    """
    if not username or not isinstance(username, str):
        return False, "Username is required"
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 40:
        return False, "Username must be at most 40 characters"
    if not USERNAME_PATTERN.match(username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, None


def validate_password(password):
    """
    Validate password strength and reject disallowed passwords.
    Returns (True, None) if valid, else (False, error_message).
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password is too long"
    if password.lower() in DISALLOWED_PASSWORDS:
        return False, "This password is too common and not allowed"
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isnumeric() for c in password)
    if not has_letter:
        return False, "Password must contain at least one letter"
    if not has_number:
        return False, "Password must contain at least one number"
    return True, None


def validate_github_url(url):
    """
    Validate that the URL is a valid GitHub profile URL.
    Empty string is valid (optional field).
    Returns (True, None) if valid, else (False, error_message).
    """
    if not url or not url.strip():
        return True, None
    url = url.strip().rstrip("/")
    if not GITHUB_URL_PATTERN.match(url):
        return False, "Please enter a valid GitHub profile URL (e.g. https://github.com/username)"
    return True, None
