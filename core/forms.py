from django import forms
from .models import Author

class AuthorProfileForm(forms.ModelForm):
    """
    Django form for editing an author's profile.
    """
    class Meta:
        model = Author
        fields = ['name', 'description', 'picture', 'github']
