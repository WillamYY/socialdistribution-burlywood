from django.db import models

"""
Author model uniquely identifies each author and can be passed around to different nodes
"""
class Author(models.Model):
    id = models.AutoField(primary_key = True) # Ensures every author has a unique id
    username = models.CharField(max_length=40)
    password = models.CharField(max_length = 40)