# core/admin.py
from django.contrib import admin
from .models import Author, AuthorRequest, HostedImage

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'github')  # columns in list
    search_fields = ('username', 'name')          # search box

@admin.register(AuthorRequest)
class AuthorRequestAdmin(admin.ModelAdmin):
    actions = ["approve","decline"] # Allows for declining and approving sign ups
    list_display = ('username','password') # Displays username and password of request

    def approve(self,request,authorrequests):
        # Loops through each author being accepted
        for authorrequest in authorrequests:
            # Gets the info from request
            authorInfo = AuthorRequest.objects.get(pk=authorrequest.id)
            # Creates the new author with it's username and password
            newAuthor = Author(id = authorInfo.id,username = authorInfo.username,name = authorInfo.name,github = authorInfo.github, picture = authorInfo.picture,picture_url =authorInfo.picture_url,host = authorInfo.host)
            newAuthor.set_password(authorInfo.password)
            newAuthor.save()
            web = f"{newAuthor.host[:len(newAuthor.host) - len("api/")]}/authors/{newAuthor.id}"
            newAuthor.web = web
            newAuthor.save()
            # Deletes the old author
            authorInfo.delete()

    """
    Upon declining delete the request and don't make a user
    """
    def decline(self,request,authorrequests):
        # Goes through every author being declined and deletes their request
        for authorrequest in authorrequests:
            AuthorRequest.objects.get(pk=authorrequest.id).delete()

@admin.register(HostedImage)
class HostedImageAdmin(admin.ModelAdmin):
    # Displays the title, upload date, and the markdown link in the admin table
    list_display = ('title', 'uploaded_at', 'image', 'get_markdown_link')
    readonly_fields = ('get_markdown_link',)
    search_fields = ('title',)

@admin.register(Node)