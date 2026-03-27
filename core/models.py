from django.db import models


class BaseModel(models.Model):
    """Abstrakte Basisklasse – alle Modelle erben created_at und updated_at."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
