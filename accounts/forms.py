from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, ROLE_CHOICES


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Passwort',
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Passwort bestätigen',
    )
    accept_privacy = forms.BooleanField(
        required=True,
        label='Ich akzeptiere die Datenschutzerklärung',
        error_messages={'required': 'Du musst die Datenschutzerklärung akzeptieren.'},
    )

    class Meta:
        model = User
        fields = ['email', 'username']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Diese E-Mail-Adresse ist bereits registriert.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Dieser Benutzername ist bereits vergeben.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw_confirm = cleaned_data.get('password_confirm')
        if pw and pw_confirm and pw != pw_confirm:
            self.add_error('password_confirm', 'Passwörter stimmen nicht überein.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='E-Mail',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        label='Passwort',
    )


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Dieser Benutzername ist bereits vergeben.')
        return username


class PasswordChangeForm(forms.Form):
    password_old = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        label='Aktuelles Passwort',
    )
    password_new = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Neues Passwort',
    )
    password_new_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Neues Passwort bestätigen',
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password_old(self):
        pw = self.cleaned_data.get('password_old')
        if not self.user.check_password(pw):
            raise ValidationError('Das aktuelle Passwort ist falsch.')
        return pw

    def clean_password_new(self):
        pw = self.cleaned_data.get('password_new')
        if pw:
            validate_password(pw, self.user)
        return pw

    def clean(self):
        cleaned_data = super().clean()
        pw_new = cleaned_data.get('password_new')
        pw_confirm = cleaned_data.get('password_new_confirm')
        if pw_new and pw_confirm and pw_new != pw_confirm:
            self.add_error('password_new_confirm', 'Passwörter stimmen nicht überein.')
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['password_new'])
        self.user.save()
        return self.user


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'is_banned', 'hide_ads']
        labels = {
            'is_banned': 'Account gesperrt',
            'hide_ads': 'Werbung ausgeblendet',
        }


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Passwort',
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'role', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Diese E-Mail-Adresse ist bereits registriert.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Dieser Benutzername ist bereits vergeben.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
