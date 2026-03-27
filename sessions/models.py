import uuid

from django.db import models

from core.models import BaseModel


class GameSession(BaseModel):
    STATUS_CHOICES = [
        ('waiting', 'Wartend'),
        ('running', 'Läuft'),
        ('finished', 'Beendet'),
    ]
    initiator = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='initiated_sessions',
        verbose_name='Initiator',
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    invite_token = models.UUIDField(
        default=uuid.uuid4, unique=True, verbose_name='Einladungs-Token',
    )
    password = models.CharField(max_length=128, verbose_name='Passwort (gehasht)')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='waiting',
        verbose_name='Status',
    )
    active_map = models.ForeignKey(
        'maps.Map',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='active_sessions',
        verbose_name='Aktive Karte',
    )
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Letzte Aktivität')

    class Meta:
        verbose_name = 'Spiel-Session'
        verbose_name_plural = 'Spiel-Sessions'

    def __str__(self):
        return self.title


class SessionParticipant(models.Model):
    ROLE_CHOICES = [
        ('gamemaster', 'Spielleiter'),
        ('player', 'Spieler'),
    ]
    session = models.ForeignKey(
        GameSession, on_delete=models.CASCADE, related_name='participants',
    )
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    character = models.ForeignKey('characters.Character', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='player')
    is_confirmed = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    is_eliminated = models.BooleanField(default=False)

    class Meta:
        unique_together = [('session', 'user')]


class CharacterPosition(models.Model):
    character = models.ForeignKey('characters.Character', on_delete=models.CASCADE)
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    map = models.ForeignKey('maps.Map', on_delete=models.CASCADE)
    x_pos = models.FloatField()
    y_pos = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class SessionEvent(models.Model):
    EVENT_TYPES = [
        ('npc_response',     'NPC-Antwort'),
        ('quest_accepted',   'Quest angenommen'),
        ('quest_declined',   'Quest abgelehnt'),
        ('item_taken',       'Item genommen'),
        ('trigger_activated', 'Trigger betätigt'),
    ]
    session = models.ForeignKey(
        GameSession, on_delete=models.CASCADE, related_name='events',
    )
    character = models.ForeignKey('characters.Character', on_delete=models.CASCADE)
    element = models.ForeignKey('maps.MapElement', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Session-Event'
        verbose_name_plural = 'Session-Events'
