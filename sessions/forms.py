from django import forms
from django.contrib.auth.hashers import check_password

from .models import GameSession, SessionParticipant


class SessionCreateForm(forms.Form):
    title = forms.CharField(
        max_length=200, label='Titel',
    )
    password_plain = forms.CharField(
        label='Passwort', widget=forms.PasswordInput(),
        help_text='Mindestens 4 Zeichen. Wird verschlüsselt gespeichert.',
    )
    character = forms.ModelChoiceField(
        queryset=None, label='Deine Figur',
        empty_label='— Figur auswählen —',
    )
    map_set = forms.ModelChoiceField(
        queryset=None, label='Karten-Set',
        empty_label='— Karten-Set auswählen —',
        required=False,
        help_text='Legt die Startkarte fest. Kann später gewechselt werden.',
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from characters.models import Character
        from maps.models import MapSet
        self.fields['character'].queryset = Character.objects.filter(
            owner=user, current_session__isnull=True,
        )
        self.fields['map_set'].queryset = MapSet.objects.filter(owner=user)

    def clean_password_plain(self):
        pw = self.cleaned_data.get('password_plain', '').strip()
        if len(pw) < 4:
            raise forms.ValidationError('Passwort muss mindestens 4 Zeichen haben.')
        return pw


class SessionJoinPasswordForm(forms.Form):
    password_plain = forms.CharField(label='Passwort', widget=forms.PasswordInput())

    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = session

    def clean_password_plain(self):
        pw = self.cleaned_data.get('password_plain', '')
        if not check_password(pw, self._session.password):
            raise forms.ValidationError('Falsches Passwort.')
        return pw


class SessionJoinCharacterForm(forms.Form):
    character = forms.ModelChoiceField(
        queryset=None, label='Figur auswählen',
        empty_label='— Figur auswählen —',
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from characters.models import Character
        self.fields['character'].queryset = Character.objects.filter(
            owner=user, current_session__isnull=True,
        )


class ParticipantRoleForm(forms.ModelForm):
    class Meta:
        model = SessionParticipant
        fields = ['role']
        labels = {'role': 'Rolle'}
