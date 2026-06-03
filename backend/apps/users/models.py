from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model where email is the unique identifier
    for authentication instead of usernames.
    """
    email = models.EmailField(unique=True)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Add any other fields you need for the portfolio admin/user

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email is USERNAME_FIELD, so it cannot be in REQUIRED_FIELDS

    def __str__(self):
        return self.email
