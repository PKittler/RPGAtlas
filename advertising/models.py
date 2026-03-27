from django.db import models
from django.utils import timezone

from core.models import BaseModel


class AdPartner(BaseModel):
    name = models.CharField(max_length=200, verbose_name='Name')
    contact_email = models.EmailField(verbose_name='Kontakt-E-Mail')

    class Meta:
        verbose_name = 'Werbepartner'
        verbose_name_plural = 'Werbepartner'

    def __str__(self):
        return self.name


class AdCampaign(BaseModel):
    partner = models.ForeignKey(
        AdPartner, on_delete=models.CASCADE, related_name='campaigns',
        verbose_name='Partner',
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    start_date = models.DateField(verbose_name='Startdatum')
    end_date = models.DateField(verbose_name='Enddatum')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')

    class Meta:
        verbose_name = 'Werbekampagne'
        verbose_name_plural = 'Werbekampagnen'

    def __str__(self):
        return self.title

    @property
    def is_running(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date


class AdIcon(BaseModel):
    campaign = models.ForeignKey(
        AdCampaign, on_delete=models.CASCADE, related_name='icons',
        verbose_name='Kampagne',
    )
    map = models.ForeignKey(
        'maps.Map', on_delete=models.CASCADE, related_name='ad_icons',
        verbose_name='Karte',
    )
    x_pos = models.FloatField(verbose_name='X-Position (0.0–1.0)')
    y_pos = models.FloatField(verbose_name='Y-Position (0.0–1.0)')
    ad_text = models.TextField(verbose_name='Werbetext')
    coupon_code = models.CharField(max_length=100, blank=True, verbose_name='Gutscheincode')
    link_url = models.URLField(blank=True, verbose_name='Link-URL')
    link_label = models.CharField(max_length=100, blank=True, verbose_name='Link-Beschriftung')
    max_clicks = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Max. Klicks (leer = unbegrenzt)',
    )
    click_count = models.PositiveIntegerField(default=0, verbose_name='Klick-Anzahl')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')

    class Meta:
        verbose_name = 'Werbe-Icon'
        verbose_name_plural = 'Werbe-Icons'

    def __str__(self):
        return f'Ad "{self.campaign.title}" auf {self.map.title}'

    def is_visible(self):
        """Alle Bedingungen für die Anzeige prüfen."""
        if not self.is_active:
            return False
        if not self.campaign.is_running:
            return False
        if self.max_clicks is not None and self.click_count >= self.max_clicks:
            return False
        return True

    def to_dict(self):
        return {
            'id': self.pk,
            'x_pos': self.x_pos,
            'y_pos': self.y_pos,
        }
