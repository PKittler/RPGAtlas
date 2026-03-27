from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager

ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('standard', 'Standard'),
    ('premium', 'Premium'),
]


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='E-Mail')
    username = models.CharField(max_length=150, unique=True, verbose_name='Benutzername')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='standard', verbose_name='Rolle')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False, verbose_name='Gesperrt')
    hide_ads = models.BooleanField(default=False, verbose_name='Werbung ausblenden')
    created_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Benutzer'
        verbose_name_plural = 'Benutzer'

    def __str__(self):
        return self.username

    def soft_delete(self):
        """DSGVO-konformes Löschen: personenbezogene Daten anonymisieren."""
        self.username = f'deleted_user_{self.pk}'
        self.email = ''
        self.is_active = False
        self.deleted_at = timezone.now()
        self.set_unusable_password()
        self.save()

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_premium(self):
        return self.role in ('admin', 'premium')
