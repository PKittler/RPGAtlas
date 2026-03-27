from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sessions'
    # Anderes Label um Konflikt mit django.contrib.sessions (label='sessions') zu vermeiden
    label = 'game_sessions'
    verbose_name = 'Spiel-Sessions'
