from django.contrib import admin

# Register your models here.
# core/admin.py
from django.contrib import admin
from .models import Author, AuthorRequest,Like,Entry

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'github')  # columns in list
    search_fields = ('username', 'name')          # search box

admin.site.register(Like)
admin.site.register(Entry)

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
            newAuthor = Author(username = authorInfo.username)
            newAuthor.set_password(authorInfo.password)
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