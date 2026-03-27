from django import forms
from django.core.exceptions import ValidationError

from maps.models import Map

from .models import AdCampaign, AdIcon, AdPartner


class AdPartnerForm(forms.ModelForm):
    class Meta:
        model = AdPartner
        fields = ['name', 'contact_email']
        labels = {
            'name': 'Name',
            'contact_email': 'Kontakt-E-Mail',
        }


class AdCampaignForm(forms.ModelForm):
    class Meta:
        model = AdCampaign
        fields = ['title', 'partner', 'start_date', 'end_date', 'is_active']
        labels = {
            'title': 'Titel',
            'partner': 'Werbepartner',
            'start_date': 'Startdatum',
            'end_date': 'Enddatum',
            'is_active': 'Aktiv',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'Das Enddatum muss nach dem Startdatum liegen.')
        return cleaned_data


class AdIconForm(forms.ModelForm):
    class Meta:
        model = AdIcon
        fields = [
            'campaign', 'map', 'x_pos', 'y_pos',
            'ad_text', 'coupon_code', 'link_url', 'link_label',
            'max_clicks', 'is_active',
        ]
        labels = {
            'campaign': 'Kampagne',
            'map': 'Karte',
            'x_pos': 'X-Position (0.0–1.0)',
            'y_pos': 'Y-Position (0.0–1.0)',
            'ad_text': 'Werbetext',
            'coupon_code': 'Gutscheincode (optional)',
            'link_url': 'Link-URL (optional)',
            'link_label': 'Link-Beschriftung (optional)',
            'max_clicks': 'Max. Klicks (leer = unbegrenzt)',
            'is_active': 'Aktiv',
        }
        widgets = {
            'ad_text': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_x_pos(self):
        val = self.cleaned_data.get('x_pos')
        if val is not None and not (0.0 <= val <= 1.0):
            raise ValidationError('X-Position muss zwischen 0.0 und 1.0 liegen.')
        return val

    def clean_y_pos(self):
        val = self.cleaned_data.get('y_pos')
        if val is not None and not (0.0 <= val <= 1.0):
            raise ValidationError('Y-Position muss zwischen 0.0 und 1.0 liegen.')
        return val
