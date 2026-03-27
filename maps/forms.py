from django import forms
from django.core.exceptions import ValidationError

from .models import Gate, Map, MapSet, NPC, Item, Trigger


class MapSetCreateForm(forms.ModelForm):
    class Meta:
        model = MapSet
        fields = ['title', 'description', 'map_type']
        widgets = {
            'map_type': forms.RadioSelect(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'map_type': 'Karten-Typ (nach dem Anlegen nicht mehr änderbar)',
        }

    def clean_map_type(self):
        mt = self.cleaned_data.get('map_type')
        if mt not in ('image', 'tiles'):
            raise ValidationError('Ungültiger Karten-Typ.')
        return mt


class MapSetEditForm(forms.ModelForm):
    class Meta:
        model = MapSet
        fields = ['title', 'description', 'allow_ads']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'allow_ads': 'Werbung auf diesem Karten-Set erlauben (Premium)',
        }


class MapAddImageForm(forms.ModelForm):
    class Meta:
        model = Map
        fields = ['title', 'image', 'is_main', 'zoom_min', 'zoom_max', 'center_x', 'center_y']
        labels = {
            'is_main': 'Als Hauptkarte des Sets festlegen',
            'center_x': 'Zentrum X (0.0 – 1.0)',
            'center_y': 'Zentrum Y (0.0 – 1.0)',
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 50 * 1024 * 1024:
                raise ValidationError('Das Bild darf maximal 50 MB groß sein.')
            if not image.content_type.startswith('image/'):
                raise ValidationError('Nur Bild-Dateien (PNG, JPG) sind erlaubt.')
        return image


class MapAddTilesForm(forms.ModelForm):
    class Meta:
        model = Map
        fields = ['title', 'tiles_file', 'is_main', 'zoom_min', 'zoom_max', 'center_x', 'center_y']
        labels = {
            'tiles_file': 'MBTiles-Datei',
            'is_main': 'Als Hauptkarte des Sets festlegen',
            'center_x': 'Zentrum X (0.0 – 1.0)',
            'center_y': 'Zentrum Y (0.0 – 1.0)',
        }

    def clean_tiles_file(self):
        f = self.cleaned_data.get('tiles_file')
        if f:
            if f.size > 500 * 1024 * 1024:
                raise ValidationError('Die MBTiles-Datei darf maximal 500 MB groß sein.')
            if not f.name.lower().endswith('.mbtiles'):
                raise ValidationError('Nur Dateien mit der Endung .mbtiles sind erlaubt.')
        return f


class GateForm(forms.ModelForm):
    class Meta:
        model = Gate
        fields = ['icon_type', 'label', 'target_map']
        labels = {
            'icon_type': 'Icon',
            'label': 'Beschriftung',
            'target_map': 'Ziel-Karte',
        }

    def __init__(self, map_set, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_map'].queryset = map_set.maps.all()
        self.fields['target_map'].required = False
        self.fields['target_map'].empty_label = '— keine Zielkarte —'


class NPCForm(forms.ModelForm):
    class Meta:
        model = NPC
        fields = ['image', 'dialogue_text', 'button_type', 'quest']
        labels = {
            'image': 'Bild (optional)',
            'dialogue_text': 'Dialogtext',
            'button_type': 'Button-Typ',
            'quest': 'Quest bei Annahme (optional)',
        }
        widgets = {
            'dialogue_text': forms.Textarea(attrs={'rows': 4}),
            'button_type': forms.RadioSelect(),
        }

    def __init__(self, map_set=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from quests.models import Quest
        if map_set:
            self.fields['quest'].queryset = Quest.objects.filter(map_set=map_set)
        else:
            self.fields['quest'].queryset = Quest.objects.none()
        self.fields['quest'].required = False
        self.fields['quest'].empty_label = '— Keine Quest —'

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 10 * 1024 * 1024:
                raise ValidationError('Das Bild darf maximal 10 MB groß sein.')
            if not image.content_type.startswith('image/'):
                raise ValidationError('Nur Bild-Dateien sind erlaubt.')
        return image


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['image', 'description_text']
        labels = {
            'image': 'Bild (optional)',
            'description_text': 'Beschreibung',
        }
        widgets = {
            'description_text': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 10 * 1024 * 1024:
                raise ValidationError('Das Bild darf maximal 10 MB groß sein.')
            if not image.content_type.startswith('image/'):
                raise ValidationError('Nur Bild-Dateien sind erlaubt.')
        return image


class TriggerForm(forms.ModelForm):
    class Meta:
        model = Trigger
        fields = ['description_text']
        labels = {
            'description_text': 'Beschreibung',
        }
        widgets = {
            'description_text': forms.Textarea(attrs={'rows': 4}),
        }
