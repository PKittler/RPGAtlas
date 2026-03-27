from django.db import models


class InventoryItem(models.Model):
    character = models.ForeignKey(
        'characters.Character', on_delete=models.CASCADE, related_name='inventory',
    )
    map_element = models.ForeignKey('maps.MapElement', on_delete=models.CASCADE)
    session = models.ForeignKey('game_sessions.GameSession', on_delete=models.CASCADE)
    picked_up_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-picked_up_at']
        verbose_name = 'Inventar-Item'
        verbose_name_plural = 'Inventar-Items'
