from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions
from core.models import OutgoingNode
import base64
import logging

logger = logging.getLogger(__name__)

class NodeBasicAuthentication(BaseAuthentication):
    def authenticate(self, request):
        #print("AUTH CLASS HIT")

        auth = get_authorization_header(request).split()
        #print("RAW AUTH HEADER:", auth)

        if not auth or auth[0].lower() != b"basic":
            #print("NO BASIC AUTH HEADER")
            raise exceptions.AuthenticationFailed("Missing basic auth header.")
            #return None

        if len(auth) != 2:
            #print("BAD AUTH HEADER LENGTH:", len(auth))
            raise exceptions.AuthenticationFailed("Invalid basic auth header.")

        try:
            decoded = base64.b64decode(auth[1]).decode("utf-8")
            #print("DECODED AUTH:", decoded)

            username, password = decoded.split(":", 1)
            logger.info("DECODED USERNAME:", username)
            logger.info("DECODED PASSWORD:", password)
        except Exception as e:
            logger.error("AUTH DECODE FAILED:", str(e))
            raise exceptions.AuthenticationFailed("Invalid basic auth encoding.")

        node = OutgoingNode.objects.filter(
            username=username,
            password=password,
            is_active=True,
        ).first()

        logger.info("MATCHED NODE:", node.url if node else None)

        if not node:
            #print("NO MATCHING OUTGOING NODE")
            raise exceptions.AuthenticationFailed("Invalid username/password.")

        #print("AUTH SUCCESS")
        return (node, None)