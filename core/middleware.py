"""
Security middleware for User Story #79: UI only communicates with node's web server.
Prevents XSS by enforcing same-origin policy via Content-Security-Policy.
"""


class SameOriginSecurityMiddleware:
    """
    Sets security headers so the UI only communicates with its own node's web server.
    Prevents the frontend from fetching/ submitting to other nodes or external APIs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content-Security-Policy: restrict UI to same-origin only
        # - connect-src 'self': fetch/XHR only to our server (key for US#79)
        # - form-action 'self': forms only submit to our server
        # - script-src 'self': scripts only from our server
        # - style-src: allow Google Fonts + inline (templates use style="")
        # - img-src: self, data: (base64), https: (profile pics from GitHub etc.)
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "form-action 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'"
        )
        response["Content-Security-Policy"] = csp

        # XSS: prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # Clickjacking: prevent embedding in iframes from other sites
        response["X-Frame-Options"] = "SAMEORIGIN"

        # Limit referrer sent to external sites
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
