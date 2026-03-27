from django import forms

from .models import Character


class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = ['name', 'description', 'avatar_image', 'color']
        labels = {
            'name': 'Name',
            'description': 'Beschreibung',
            'avatar_image': 'Avatar-Bild (optional)',
            'color': 'Farbe',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 cursor-pointer rounded border border-gray-600 bg-transparent p-0.5'}),
        }
