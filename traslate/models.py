
# Create your models here.
from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    email_verified = models.BooleanField(default=False)
    
    


class Translation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Relación con el usuario
    original_text = models.TextField()  # Texto original en español
    hebrew_text = models.TextField()  # Traducción al hebreo
    cabala_value = models.IntegerField(null=False, blank=False)  # Valor numerológico en la Cábala
    created_at = models.DateTimeField(default=timezone.now)  # Fecha de creación

    def __str__(self):
        return f"{self.original_text} -> {self.hebrew_text} ({self.cabala_value})"