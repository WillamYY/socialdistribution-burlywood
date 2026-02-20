from django.db import models

"""
Author model uniquely identifies each author and can be passed around to different nodes
"""
class Author(models.Model):
    username = models.CharField(max_length=40,unique = True)
    password = models.CharField()
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    picture = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    github = models.URLField(blank=True)
    id = models.AutoField(primary_key = True) # Ensures every author has a unique id

