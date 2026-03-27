from django.db import models
from core.models import BaseModel


class Quest(BaseModel):
    map_set = models.ForeignKey(
        'maps.MapSet', on_delete=models.CASCADE, related_name='quests',
        verbose_name='Karten-Set',
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    description = models.TextField(blank=True, verbose_name='Beschreibung')

    class Meta:
        verbose_name = 'Quest'
        verbose_name_plural = 'Quests'

    def __str__(self):
        return self.title


class QuestStep(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(verbose_name='Reihenfolge')
    description = models.TextField(verbose_name='Beschreibung')

    class Meta:
        ordering = ['order']
        verbose_name = 'Quest-Schritt'
        verbose_name_plural = 'Quest-Schritte'


class CharacterQuest(models.Model):
    STATUS_CHOICES = [
        ('active', 'Aktiv'),
        ('completed', 'Abgeschlossen'),
        ('failed', 'Fehlgeschlagen'),
    ]
    character = models.ForeignKey('characters.Character', on_delete=models.CASCADE)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    session = models.ForeignKey('game_sessions.GameSession', on_delete=models.CASCADE)
    current_step = models.ForeignKey(
        QuestStep, on_delete=models.SET_NULL, null=True, blank=True,
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        unique_together = [('character', 'quest', 'session')]
