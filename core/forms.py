from django import forms
from .models import Author

class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['name', 'description', 'picture', 'github']
