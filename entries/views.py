import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Entry
from core.models import Author

"""
Handles the creation of a new entry, including processing image uploads and text content.
"""
@login_required
def create_entry(request):
    if request.method == 'POST':
        # Get the author first
        author = Author.objects.get(id=request.user.id)

        # Extract standard text fields from the form
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        visibility = request.POST.get('visibility', 'PUBLIC')
        content_type = request.POST.get('contentType', 'text/plain')
        
        content = ""
        
        # Check if the user is uploading an image
        if content_type in ['image/png;base64', 'image/jpeg;base64', 'application/base64']:
            # request.FILES should contain the uploaded files
            if 'image_file' in request.FILES:
                uploaded_image = request.FILES['image_file']
                # Read the binary data and encode it to a base64 string
                base64_encoded = base64.b64encode(uploaded_image.read()).decode('utf-8')
                content = base64_encoded
        else:
            # If no image, just grab the text/markdown content
            content = request.POST.get('content', '')
        
        # Save the entry to the database
        new_entry = Entry.objects.create(
            author=author,
            title=title,
            description=description,
            contentType=content_type,
            content=content,
            visibility=visibility
        )
        
        # Redirect the user back to my-entries page
        return redirect("my_entries")

    # Show the empty form for GET requests
    return render(request, 'entries/create_entry.html')

@login_required
def my_entries(request):
    author = Author.objects.get(id=request.user.id)

    # Get all entries by this author, ordered by newest first
    entries = Entry.objects.filter(author=author).order_by('-published')
    
    return render(request, 'entries/my_entries.html', {'entries': entries})