from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True)
    bio = models.CharField(max_length=280, blank=True)
    preferred_language = models.CharField(max_length=5, choices=(("ar", "العربية"), ("en", "English")), default="ar")
    email_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ("username",)

    def __str__(self):
        return self.username
