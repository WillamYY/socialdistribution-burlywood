from django.db import models


"""
Node model that stores information about node admin and all those in a node
"""
class Node(models.Model):
    id = models.AutoField(primary_key = True)
    admin_id = models.IntegerField(default = 0)

"""
Author model uniquely identifies each author and can be passed around to different nodes
"""
class Author(models.Model):
    id = models.AutoField(primary_key = True) # Ensures every author has a unique id
    username = models.CharField(max_length=40)
    password = models.CharField(max_length = 40)
    node = models.ForeignKey(Node,on_delete=models.CASCADE,null = True) # Makes each author specific to a node