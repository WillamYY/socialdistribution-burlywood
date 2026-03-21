# core/admin.py
import base64
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
from .models import Author, AuthorRequest, AdminHostedImage, IncomingNode, OutgoingNode
from .validators import validate_username, validate_password
import re, IncomingNode, OutgoingNode
from .validators import validate_username, validate_password
import re

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
            web = f"{newAuthor.host[:len(newAuthor.host) - len("api/")]}/app/user/{newAuthor.id}"
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

class AdminHostedImageAdminForm(forms.ModelForm):
    """
    Customed form to upload hosted images in admin panel.
    """
    upload_image = forms.ImageField(required=False)

    class Meta:
        model = AdminHostedImage
        fields = ["title"]

    def clean_upload_image(self):
        image = self.cleaned_data.get("upload_image")
        if image and image.content_type not in ["image/png", "image/jpeg"]:
            raise forms.ValidationError("Only PNG and JPEG images are allowed.")
        return image

@admin.register(AdminHostedImage)
class HostedImageAdmin(admin.ModelAdmin):
    form = AdminHostedImageAdminForm
    list_display = ("title", "content_type", "uploaded_at", "preview")
    readonly_fields = ("content_type", "preview")
    fields = ("title", "upload_image", "content_type", "preview")

    def save_model(self, request, obj, form, change):
        """
        Encode uploaded images in base64.
        """
        upload = form.cleaned_data.get("upload_image")
        if upload:
            obj.content_type = upload.content_type
            obj.content = base64.b64encode(upload.read()).decode("utf-8")
        super().save_model(request, obj, form, change)

    def preview(self, obj):
        """
        Rendere a <img> html for image preview.
        """
        if obj.content and obj.content_type:
            return format_html(
                '<img src="data:{};base64,{}" style="max-height:120px; max-width:200px;" />',
                obj.content_type,
                obj.content,
            )
        return "No image"

    preview.short_description = "Preview"

"""
Creates the form that validates input
"""
class IncomingNodeAdminForm(forms.ModelForm):
    class Meta:
        model = IncomingNode
        fields = ["url","username","password"]
    """
    Validates and ensures a proper password
    """
    def clean_password(self):
        password = self.cleaned_data.get("password")
        ok, error = validate_password(password)
        if not ok:
            raise ValidationError(error)
        return password
    """
    Validates the url
    """
    def clean_url(self):
        url = self.cleaned_data.get("url")
        reMatch = re.search(f"^https?://[^/]+/$",url)
        if reMatch:
            return url
        else:
            raise ValidationError("Please enter valid host")

@admin.register(IncomingNode)
class IncomingNodeAdmin(admin.ModelAdmin):
    list_display = ('url','username')
    form = IncomingNodeAdminForm

"""
Creates the form that validates input
"""
class OutgoingNodeAdminForm(forms.ModelForm):
    class Meta:
        model = OutgoingNode
        fields = ["url","username","password","is_active"]
    """
    Validates and ensures a proper password
    """
    def clean_password(self):
        password = self.cleaned_data.get("password")
        ok, error = validate_password(password)
        if not ok:
            raise ValidationError(error)
        return password
    """
    Validates the url
    """
    def clean_url(self):
        url = self.cleaned_data.get("url")
        reMatch = re.search(f"^https?://[^/]+/$",url)
        if reMatch:
            return url
        else:
            raise ValidationError("Please enter valid host")

@admin.register(OutgoingNode)
class OutgoingNodeAdmin(admin.ModelAdmin):
    list_display = ('url','username')
    form = OutgoingNodeAdminForm
  

"""
Creates the form that validates input
"""
class IncomingNodeAdminForm(forms.ModelForm):
    class Meta:
        model = IncomingNode
        fields = ["url","username","password"]
    """
    Validates and ensures a proper password
    """
    def clean_password(self):
        password = self.cleaned_data.get("password")
        ok, error = validate_password(password)
        if not ok:
            raise ValidationError(error)
        return password
    """
    Validates the url
    """
    def clean_url(self):
        url = self.cleaned_data.get("url")
        reMatch = re.search(f"^https?://[^/]+/$",url)
        if reMatch:
            return url
        else:
            raise ValidationError("Please enter valid host")

@admin.register(IncomingNode)
class IncomingNodeAdmin(admin.ModelAdmin):
    list_display = ('url','username')
    form = IncomingNodeAdminForm

"""
Creates the form that validates input
"""
class OutgoingNodeAdminForm(forms.ModelForm):
    class Meta:
        model = OutgoingNode
        fields = ["url","username","password","is_active"]
    """
    Validates and ensures a proper password
    """
    def clean_password(self):
        password = self.cleaned_data.get("password")
        ok, error = validate_password(password)
        if not ok:
            raise ValidationError(error)
        return password
    """
    Validates the url
    """
    def clean_url(self):
        url = self.cleaned_data.get("url")
        reMatch = re.search(f"^https?://[^/]+/$",url)
        if reMatch:
            return url
        else:
            raise ValidationError("Please enter valid host")

@admin.register(OutgoingNode)
class OutgoingNodeAdmin(admin.ModelAdmin):
    list_display = ('url','username')
    form = OutgoingNodeAdminForm
  