from django.db import models

from core.models import BaseModel

GATE_ICON_CHOICES = [
    ('city',      'Stadt'),
    ('village',   'Dorf'),
    ('cave',      'Höhle'),
    ('plateau',   'Plateau'),
    ('canyon',    'Canyon'),
    ('trapdoor',  'Falltür'),
    ('stairs',    'Treppe'),
    ('ladder',    'Leiter'),
    ('hole',      'Loch'),
]

ELEMENT_TYPE_CHOICES = [
    ('npc',     'NPC'),
    ('item',    'Item'),
    ('trigger', 'Trigger'),
]


class MapSet(BaseModel):
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='mapsets',
        verbose_name='Eigentümer',
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    map_type = models.CharField(
        max_length=6,
        choices=[('image', 'Bild-Karte'), ('tiles', 'Kachel-Karte')],
        verbose_name='Karten-Typ',
    )
    allow_ads = models.BooleanField(default=True, verbose_name='Werbung erlaubt')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Karten-Set'
        verbose_name_plural = 'Karten-Sets'

    def __str__(self):
        return self.title


class Map(BaseModel):
    map_set = models.ForeignKey(
        MapSet, on_delete=models.CASCADE, related_name='maps',
        verbose_name='Karten-Set',
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    is_main = models.BooleanField(default=False, verbose_name='Hauptkarte')

    # Bild-Karten
    image = models.ImageField(
        upload_to='maps/images/', null=True, blank=True, verbose_name='Kartenbild',
    )
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)

    # Kachel-Karten
    tiles_file = models.FileField(
        upload_to='maps/tiles/', null=True, blank=True, verbose_name='MBTiles-Datei',
    )
    tiles_url = models.CharField(
        max_length=500, blank=True, verbose_name='Kachel-URL (intern)',
    )
    tiles_bounds = models.JSONField(
        null=True, blank=True,
        help_text='{"west": float, "south": float, "east": float, "north": float}',
    )

    zoom_min = models.IntegerField(default=1, verbose_name='Zoom min')
    zoom_max = models.IntegerField(default=10, verbose_name='Zoom max')
    center_x = models.FloatField(default=0.5, verbose_name='Zentrum X (0.0–1.0)')
    center_y = models.FloatField(default=0.5, verbose_name='Zentrum Y (0.0–1.0)')

    class Meta:
        ordering = ['-is_main', 'title']
        verbose_name = 'Karte'
        verbose_name_plural = 'Karten'

    def __str__(self):
        return f'{self.map_set.title} – {self.title}'


class Gate(models.Model):
    source_map = models.ForeignKey(
        Map, on_delete=models.CASCADE, related_name='gates',
        verbose_name='Quell-Karte',
    )
    target_map = models.ForeignKey(
        Map, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='incoming_gates',
        verbose_name='Ziel-Karte',
    )
    icon_type = models.CharField(
        max_length=20, choices=GATE_ICON_CHOICES, verbose_name='Icon-Typ',
    )
    label = models.CharField(max_length=100, verbose_name='Bezeichnung')
    x_pos = models.FloatField(verbose_name='X-Position (0.0–1.0)')
    y_pos = models.FloatField(verbose_name='Y-Position (0.0–1.0)')

    class Meta:
        verbose_name = 'Gate'
        verbose_name_plural = 'Gates'

    def __str__(self):
        return f'{self.label} ({self.icon_type}) @ {self.source_map.title}'

    def to_dict(self):
        return {
            'id': self.pk,
            'icon_type': self.icon_type,
            'label': self.label,
            'x_pos': self.x_pos,
            'y_pos': self.y_pos,
            'target_map_id': self.target_map_id,
        }


class MapElement(models.Model):
    map = models.ForeignKey(
        Map, on_delete=models.CASCADE, related_name='elements',
        verbose_name='Karte',
    )
    element_type = models.CharField(
        max_length=10, choices=ELEMENT_TYPE_CHOICES, verbose_name='Typ',
    )
    x_pos = models.FloatField(verbose_name='X-Position (0.0–1.0)')
    y_pos = models.FloatField(verbose_name='Y-Position (0.0–1.0)')
    is_conditional = models.BooleanField(
        default=False, verbose_name='Bedingt sichtbar',
    )

    class Meta:
        verbose_name = 'Karten-Element'
        verbose_name_plural = 'Karten-Elemente'

    def to_dict(self):
        return {
            'id': self.pk,
            'element_type': self.element_type,
            'x_pos': self.x_pos,
            'y_pos': self.y_pos,
            'is_conditional': self.is_conditional,
        }


class ElementCondition(models.Model):
    element = models.ForeignKey(
        MapElement, on_delete=models.CASCADE, related_name='conditions',
    )
    required_quest = models.ForeignKey(
        'quests.Quest', on_delete=models.SET_NULL, null=True, blank=True,
    )
    condition_type = models.CharField(max_length=50)
    condition_value = models.CharField(max_length=200)


class NPC(models.Model):
    BUTTON_CHOICES = [
        ('accept_decline_later', 'Annehmen / Ablehnen / Später'),
        ('yes_no', 'Ja / Nein'),
        ('none', 'Keine Buttons'),
    ]
    element = models.OneToOneField(
        MapElement, on_delete=models.CASCADE, related_name='npc',
    )
    image = models.ImageField(
        upload_to='maps/npcs/', null=True, blank=True, verbose_name='Bild',
    )
    dialogue_text = models.TextField(verbose_name='Dialogtext')
    button_type = models.CharField(
        max_length=30, choices=BUTTON_CHOICES, default='none', verbose_name='Button-Typ',
    )
    quest = models.ForeignKey(
        'quests.Quest', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Quest bei Annahme (optional)',
    )


class Item(models.Model):
    element = models.OneToOneField(
        MapElement, on_delete=models.CASCADE, related_name='item',
    )
    image = models.ImageField(
        upload_to='maps/items/', null=True, blank=True, verbose_name='Bild',
    )
    description_text = models.TextField(verbose_name='Beschreibung')


class Trigger(models.Model):
    element = models.OneToOneField(
        MapElement, on_delete=models.CASCADE, related_name='trigger',
    )
    description_text = models.TextField(verbose_name='Beschreibung')
