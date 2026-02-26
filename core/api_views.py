# core/api_views.py  (or add to core/views.py)
import json
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import Author

@csrf_exempt
def api_author_detail(request, author_id):
    """
    GET: return author info (public/private fields depending on session)
    PUT: update profile fields for the logged in author only (session auth)
    """
    try:
        author = Author.objects.get(pk=author_id)
    except Author.DoesNotExist:
        return JsonResponse({"error": "Author not found"}, status=404)

    logged_id = request.session.get("author_id")

    if request.method == "GET":
        # Return basic author data
        return JsonResponse({
            "id": author.id,
            "username": author.username,
            "name": author.name,
            "description": author.description,
            "github": author.github,
            # picture could be a URL if available
            "picture": author.picture.url if author.picture else None,
        })

    elif request.method == "PUT":
        if not logged_id:
            return JsonResponse({"error": "Authentication required"}, status=401)
        if int(logged_id) != int(author_id):
            return HttpResponseForbidden(json.dumps({"error": "Not allowed to edit"}), content_type="application/json")

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Allowed fields
        for field in ("username", "name", "description", "github"):
            if field in body:
                value = body.get(field)
                if field == "username" and value != author.username:
                    # check unique username
                    if Author.objects.filter(username=value).exists():
                        return JsonResponse({"error": "Username already taken"}, status=400)
                    author.username = value
                    # update session username
                    request.session["username"] = value
                else:
                    setattr(author, field, value)

        author.save()

        return JsonResponse({
            "message": "Updated",
            "author": {
                "id": author.id,
                "username": author.username,
                "name": author.name,
                "description": author.description,
                "github": author.github,
                "picture": author.picture.url if author.picture else None,
            }
        }, status=200)

    else:
        return HttpResponseNotAllowed(["GET", "PUT"])