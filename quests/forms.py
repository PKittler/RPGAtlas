from django import forms

from .models import Quest, QuestStep


class QuestForm(forms.ModelForm):
    class Meta:
        model = Quest
        fields = ['title', 'description']
        labels = {'title': 'Titel', 'description': 'Beschreibung'}
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class QuestStepForm(forms.ModelForm):
    class Meta:
        model = QuestStep
        fields = ['description']
        labels = {'description': 'Schritt-Beschreibung'}
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
