from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class AdminRequiredMixin(LoginRequiredMixin):
    """Schränkt Zugriff auf Nutzer mit role='admin' ein."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class OwnerRequiredMixin(LoginRequiredMixin):
    """Schränkt Zugriff auf den Eigentümer eines Objekts ein (oder Admin)."""
    owner_field = 'owner'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        owner = getattr(obj, self.owner_field)
        if owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied
        return obj


class PremiumRequiredMixin(LoginRequiredMixin):
    """Schränkt Zugriff auf Premium- und Admin-Nutzer ein."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_premium:
            messages.error(request, 'Diese Funktion ist nur für Premium-Nutzer verfügbar.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
