from django.db import models
from core.models import BaseModel


class Character(BaseModel):
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='characters',
        verbose_name='Eigentümer',
    )
    name = models.CharField(max_length=200, verbose_name='Name')
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    avatar_image = models.ImageField(
        upload_to='characters/avatars/', null=True, blank=True,
        verbose_name='Avatar',
    )
    color = models.CharField(max_length=7, default='#6366f1', verbose_name='Farbe (Hex)')
    current_session = models.ForeignKey(
        'game_sessions.GameSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='active_characters',
        verbose_name='Aktive Session',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Figur'
        verbose_name_plural = 'Figuren'

    def __str__(self):
        return self.name
