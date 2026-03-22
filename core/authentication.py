import base64

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions

from core.models import OutgoingNode


class NodeBasicAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b"basic":
            return None

        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Invalid basic auth header.")

        try:
            decoded = base64.b64decode(auth[1]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid basic auth encoding.")

        node = OutgoingNode.objects.filter(
            username=username,
            password=password,
            is_active=True,
        ).first()

        if not node:
            raise exceptions.AuthenticationFailed("Invalid username/password.")

        return (node, None)