# User Story #79: UI Only Communicates with Node's Web Server

**As a node admin**, I want my node's UI to only communicate with my node's web server, **so I can prevent XSS.**

## Implementation

### 1. Content-Security-Policy (CSP)

`SameOriginSecurityMiddleware` (`core/middleware.py`) sets a strict CSP:

- **`connect-src 'self'`** – Fetch/XHR/Ajax only to the same origin; blocks UI from calling other nodes or external APIs
- **`form-action 'self'`** – Forms submit only to this server
- **`script-src 'self'`** – Scripts load only from this server
- **`style-src`** – Allows `'self'`, `'unsafe-inline'`, and `https://fonts.googleapis.com` for styling
- **`font-src`** – Allows `'self'` and `https://fonts.gstatic.com` for Google Fonts
- **`img-src`** – Allows `'self'`, `data:`, and `https:` (e.g., profile pictures from GitHub)
- **`frame-ancestors 'self'`** – Page cannot be embedded in iframes from other origins
- **`base-uri 'self'`** – Restricts base tag URLs

### 2. Other Security Headers

- **X-Content-Type-Options: nosniff** – Prevents MIME type sniffing (XSS mitigation)
- **X-Frame-Options: SAMEORIGIN** – Prevents clickjacking
- **Referrer-Policy: strict-origin-when-cross-origin** – Limits referrer leakage

### 3. JavaScript Same-Origin Check

`entries/static/entries/js/main.js` uses `isSameOrigin()` for elements with `data-url`:

- Relative URLs (e.g. `/app/stream/`) are treated as same-origin
- Absolute URLs must match `hostname` and `protocol`
- External URLs are not followed via the clickable handler (prevents redirects to malicious sites via stored URLs)

### 4. Out-of-Scope

- Normal hyperlinks (e.g. to GitHub) still work – CSP does not block user-initiated navigation
- API-to-API communication between nodes is server-side and unchanged

## Testing

```bash
python manage.py test core.tests.SameOriginSecurityMiddlewareTestCase
```

## Documentation

- Middleware: `core/middleware.py`
- JS guard: `entries/static/entries/js/main.js`
-API Documentation

## Citation
- For documentation and some error fixing, used genAI for formatting help.
Prompt- "Help me clean the formatting for this document and make it look tidy"
